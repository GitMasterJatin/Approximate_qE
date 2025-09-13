
import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 font-sans">
      <div className="text-center text-white max-w-2xl px-5 py-10">
        <h1 className="text-5xl font-bold mb-4 tracking-tight">
          Welcome to Your App
        </h1>
        <p className="text-xl mb-8 opacity-90 leading-relaxed">
          Experience a modern, secure login system with beautiful design and smooth interactions.
        </p>
        <Link 
          href="/login"
          className="inline-block bg-white text-indigo-600 px-8 py-4 rounded-xl font-semibold text-lg shadow-lg hover:shadow-xl transform hover:-translate-y-1 transition-all duration-200 hover:bg-gray-50"
        >
          Go to Login Page
        </Link>
      </div>
    </div>
  );
}