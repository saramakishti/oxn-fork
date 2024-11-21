'use client'
import { Button } from "@/components/ui/button";

export default function ErrorPage({ error, reset }: { error: Error; reset: () => void }) {

  return (
    <div className="flex flex-col items-center justify-center">
      <h1 className="text-3xl mb-4">Something went wrong</h1>
      <p className="mb-6">{error?.message || 'An unexpected error has occurred.'}</p>
      <Button
        onClick={() => reset()}
        className="px-4 py-2"
      >
        Try Again
      </Button>
    </div>
  )
}