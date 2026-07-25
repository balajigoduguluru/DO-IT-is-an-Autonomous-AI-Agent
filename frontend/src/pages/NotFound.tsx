import { Link } from 'react-router-dom';
import { AlertCircle } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-do-bg-primary text-do-text-primary flex flex-col items-center justify-center font-sans">
      <AlertCircle className="w-16 h-16 text-do-warning mb-6" />
      <h1 className="text-4xl font-bold mb-4">404 - Sector Not Found</h1>
      <p className="text-do-text-secondary mb-8 text-lg">The autonomous agent couldn't locate this route.</p>
      <Link 
        to="/"
        className="bg-do-text-primary text-do-bg-primary px-6 py-3 rounded-do-radius-full font-medium hover:scale-95 transition-transform"
      >
        Return to Mission Control
      </Link>
    </div>
  );
}
