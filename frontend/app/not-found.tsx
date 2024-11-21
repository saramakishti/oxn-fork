import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center h-screen">
      <h1 className="text-3xl mb-4">404 - Page Not Found</h1>
      <p className="mb-6">The page you are looking for does not exist or has been moved.</p>
      <Link href="/" className="px-4 py-2">
        <Button>
          Go Back Home
        </Button>
      </Link>
    </div>
  );
}