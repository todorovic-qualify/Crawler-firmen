import { getServerSession } from 'next-auth';
import { redirect } from 'next/navigation';
import { authOptions } from '@/lib/auth';
import LoginPage from '@/components/LoginPage';

export default async function Home() {
  const session = await getServerSession(authOptions);
  if (session?.accessToken) redirect('/dashboard');
  return <LoginPage />;
}
