"use client"

import { useRouter, useSearchParams } from "next/navigation"
import { useState, useRef, useEffect } from 'react'

export default function VerifyOTP() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const email = searchParams.get("email")

  const [otp, setOtp] = useState<string[]>(['', '', '', '', '', ''])
  const [verified, setVerified] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [shake, setShake] = useState(false)

  const [timer, setTimer] = useState(30)
  const [canResend, setCanResend] = useState(false)

  const inputs = useRef<Array<HTMLInputElement | null>>([])

  /* ⏳ Countdown */
  useEffect(() => {
    if (timer === 0) {
      setCanResend(true)
      return
    }

    const interval = setInterval(() => {
      setTimer((prev) => prev - 1)
    }, 1000)

    return () => clearInterval(interval)
  }, [timer])

  /* 🔢 OTP input */
  const handleChange = (value: string, index: number) => {
    if (!/^\d?$/.test(value)) return

    const newOtp = [...otp]
    newOtp[index] = value
    setOtp(newOtp)

    if (value && index < 5) {
      inputs.current[index + 1]?.focus()
    }
  }

  const handleKeyDown = (
    e: React.KeyboardEvent<HTMLInputElement>,
    index: number
  ) => {
    if (e.key === 'Backspace' && otp[index] === '' && index > 0) {
      inputs.current[index - 1]?.focus()
    }
  }

  const isComplete = otp.every((d) => d !== '')

  /* ✅ VERIFY */
  const handleVerify = async () => {
    if (!isComplete) return

    setLoading(true)
    setError('')

    // 🔁 simulate API check
    await new Promise((res) => setTimeout(res, 1200))

    const isValid = otp.join('') === '123456' // mock OTP

    if (!isValid) {
      setError('Invalid or expired OTP')
      setShake(true)
      setTimeout(() => setShake(false), 400)
      setLoading(false)
      return
    }

    setVerified(true)
    setLoading(false)

    setTimeout(() => {
      router.push('/login')
    }, 2000)
  }

  /* 🔁 RESEND */
  const handleResend = () => {
    if (!canResend) return

    setOtp(['', '', '', '', '', ''])
    setTimer(30)
    setCanResend(false)
    setError('')
    inputs.current[0]?.focus()
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800 px-4">
      <div
        className={`bg-white p-8 rounded-2xl shadow-2xl w-full max-w-md text-center transition
        ${shake ? 'animate-shake' : ''}`}
      >
        {!verified ? (
          <>
            <h2 className="text-2xl font-semibold mb-2">
              Verify OTP
            </h2>
            <p className="text-sm text-gray-500 mb-6">
              Enter the 6-digit code sent to your email
            </p>

            {/* OTP INPUTS */}
            <div className="flex justify-between mb-4">
              {otp.map((digit, index) => (
                <input
                  key={index}
                  ref={(el) => {
                    inputs.current[index] = el
                  }}
                  type="text"
                  maxLength={1}
                  value={digit}
                  onChange={(e) => handleChange(e.target.value, index)}
                  onKeyDown={(e) => handleKeyDown(e, index)}
                  className="w-12 h-12 border rounded-lg text-center text-lg font-semibold
                  focus:ring-2 focus:ring-blue-500 outline-none"
                />
              ))}
            </div>

            {error && (
              <p className="text-red-500 text-sm mb-3">
                {error}
              </p>
            )}

            <button
              disabled={!isComplete || loading}
              onClick={handleVerify}
              className={`w-full py-2.5 rounded-lg text-white font-medium transition
              ${
                isComplete
                  ? 'bg-blue-600 hover:bg-blue-700'
                  : 'bg-gray-400 cursor-not-allowed'
              }`}
            >
              {loading ? 'Verifying…' : 'Verify & Create Account'}
            </button>

            <div className="mt-4 text-sm">
              {!canResend ? (
                <p className="text-gray-500">
                  Resend OTP in <span className="font-semibold">{timer}s</span>
                </p>
              ) : (
                <button
                  onClick={handleResend}
                  className="text-blue-600 hover:underline"
                >
                  Resend OTP
                </button>
              )}
            </div>
          </>
        ) : (
          <div className="py-8 animate-scaleIn">
            <div className="text-5xl mb-3">✅</div>
            <h3 className="text-xl font-semibold text-green-600">
              Account Created Successfully
            </h3>
            <p className="text-sm text-gray-500 mt-2">
              Redirecting to login…
            </p>
          </div>
        )}
      </div>

      <style jsx>{`
        .animate-shake {
          animation: shake 0.4s;
        }
        @keyframes shake {
          0% { transform: translateX(0); }
          25% { transform: translateX(-6px); }
          50% { transform: translateX(6px); }
          75% { transform: translateX(-6px); }
          100% { transform: translateX(0); }
        }

        .animate-scaleIn {
          animation: scaleIn 0.4s ease-out;
        }
        @keyframes scaleIn {
          from { transform: scale(0.8); opacity: 0; }
          to { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </div>
  )
}
