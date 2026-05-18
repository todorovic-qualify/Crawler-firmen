import os
import json
from collections import defaultdict
from flask import (Flask, redirect, url_for, session, request,
                   render_template, jsonify, Response, stream_with_context)
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'gmail-cleanup-dev-secret')

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), 'credentials.json')

# Allow HTTP for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'


def get_service():
    if 'credentials' not in session:
        return None
    return build('gmail', 'v1', credentials=Credentials(**session['credentials']))


@app.route('/')
def index():
    has_creds_file = os.path.exists(CREDENTIALS_FILE)
    is_authed = 'credentials' in session
    return render_template('index.html', has_creds_file=has_creds_file, is_authed=is_authed)


@app.route('/auth')
def auth():
    if not os.path.exists(CREDENTIALS_FILE):
        return redirect(url_for('index'))
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('callback', _external=True)
    )
    url, state = flow.authorization_url(access_type='offline', prompt='consent')
    session['state'] = state
    return redirect(url)


@app.route('/callback')
def callback():
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        state=session.get('state'),
        redirect_uri=url_for('callback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)
    c = flow.credentials
    session['credentials'] = {
        'token': c.token,
        'refresh_token': c.refresh_token,
        'token_uri': c.token_uri,
        'client_id': c.client_id,
        'client_secret': c.client_secret,
        'scopes': list(c.scopes or [])
    }
    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/api/stream')
def stream():
    if 'credentials' not in session:
        return jsonify({'error': 'Nicht angemeldet'}), 401

    creds_dict = dict(session['credentials'])
    limit = min(int(request.args.get('limit', 500)), 5000)
    label = request.args.get('label', 'INBOX')

    def generate():
        try:
            svc = build('gmail', 'v1', credentials=Credentials(**creds_dict))
            senders = defaultdict(lambda: {'ids': [], 'subjects': []})
            loaded = 0
            page_token = None

            yield f"data: {json.dumps({'type': 'start', 'limit': limit})}\n\n"

            while loaded < limit:
                fetch_size = min(100, limit - loaded)
                params = {
                    'userId': 'me',
                    'maxResults': fetch_size,
                    'labelIds': [label]
                }
                if page_token:
                    params['pageToken'] = page_token

                result = svc.users().messages().list(**params).execute()
                msgs = result.get('messages', [])
                if not msgs:
                    break

                # Batch-Fetch der Metadaten (50 pro Batch)
                for batch_start in range(0, len(msgs), 50):
                    batch_msgs = msgs[batch_start:batch_start + 50]
                    batch_results = {}

                    def make_callback(msg_id):
                        def cb(req_id, response, exception):
                            if exception is None:
                                batch_results[msg_id] = response
                        return cb

                    batch = svc.new_batch_http_request()
                    for m in batch_msgs:
                        batch.add(
                            svc.users().messages().get(
                                userId='me',
                                id=m['id'],
                                format='metadata',
                                metadataHeaders=['From', 'Subject']
                            ),
                            request_id=m['id'],
                            callback=make_callback(m['id'])
                        )
                    batch.execute()

                    for msg_id, detail in batch_results.items():
                        headers = {
                            h['name']: h['value']
                            for h in detail.get('payload', {}).get('headers', [])
                        }
                        sender = headers.get('From', 'Unbekannt')
                        subject = headers.get('Subject', '(kein Betreff)')
                        senders[sender]['ids'].append(msg_id)
                        if subject not in senders[sender]['subjects']:
                            senders[sender]['subjects'].append(subject)
                        loaded += 1

                    yield f"data: {json.dumps({'type': 'progress', 'loaded': loaded})}\n\n"

                page_token = result.get('nextPageToken')
                if not page_token:
                    break

            groups = sorted(
                [
                    {
                        'sender': s,
                        'count': len(d['ids']),
                        'ids': d['ids'],
                        'subjects': d['subjects'][:60]
                    }
                    for s, d in senders.items()
                ],
                key=lambda x: x['count'],
                reverse=True
            )

            yield f"data: {json.dumps({'type': 'done', 'groups': groups, 'total': loaded})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


@app.route('/api/trash', methods=['POST'])
def trash():
    svc = get_service()
    if not svc:
        return jsonify({'error': 'Nicht angemeldet'}), 401
    ids = request.json.get('ids', [])
    try:
        for i in range(0, len(ids), 1000):
            svc.users().messages().batchModify(
                userId='me',
                body={
                    'ids': ids[i:i + 1000],
                    'addLabelIds': ['TRASH'],
                    'removeLabelIds': ['INBOX']
                }
            ).execute()
        return jsonify({'success': True, 'count': len(ids)})
    except HttpError as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete', methods=['POST'])
def delete():
    svc = get_service()
    if not svc:
        return jsonify({'error': 'Nicht angemeldet'}), 401
    ids = request.json.get('ids', [])
    try:
        for i in range(0, len(ids), 1000):
            svc.users().messages().batchDelete(
                userId='me',
                body={'ids': ids[i:i + 1000]}
            ).execute()
        return jsonify({'success': True, 'count': len(ids)})
    except HttpError as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
