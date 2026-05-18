import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';
import { authOptions } from '@/lib/auth';
import Dashboard from '@/components/Dashboard';

export default async function DashboardPage() {
  const session = await getServerSession(authOptions);
  if (!session?.accessToken) redirect('/');

  return (
    <Dashboard
      userEmail={session.user?.email ?? ''}
      userName={session.user?.name ?? ''}
      userImage={session.user?.image ?? null}
      hasTokenError={session.error === 'RefreshAccessTokenError'}
    />
  );
}
