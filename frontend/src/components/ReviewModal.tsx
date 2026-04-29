import React, { useState } from 'react';
import { motion } from 'motion/react';
import { X, Star, Gift, Send } from 'lucide-react';
import { Button } from './ui/button';

interface ReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ReviewModal({ isOpen, onClose }: ReviewModalProps) {
  const [rating, setRating] = useState(5);
  const [hoveredRating, setHoveredRating] = useState(0);
  const [reviewText, setReviewText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async () => {
    if (reviewText.trim().length < 10) {
      alert("이용후기를 10자 이상 작성해주세요.");
      return;
    }

    setIsSubmitting(true);
    // TODO: 백엔드 API 연동
    setTimeout(() => {
      setIsSubmitting(false);
      setIsSubmitted(true);
    }, 1000);
  };

  const handleClose = () => {
    setIsSubmitted(false);
    setReviewText('');
    setRating(5);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm">
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="w-full max-w-lg bg-white rounded-3xl overflow-hidden shadow-2xl relative flex flex-col"
      >
        <button onClick={handleClose} className="absolute top-4 right-4 z-10 p-2 text-slate-400 hover:text-slate-600 bg-slate-50 rounded-full transition-colors">
          <X size={20} />
        </button>

        {isSubmitted ? (
          <div className="p-8 sm:p-14 text-center flex flex-col items-center">
            <div className="w-20 h-20 sm:w-24 sm:h-24 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mb-6 sm:mb-8">
              <Gift size={40} className="sm:w-12 sm:h-12" />
            </div>
            <h2 className="text-2xl sm:text-3xl font-black text-slate-800 mb-4">소중한 후기 감사합니다!</h2>
            <p className="text-slate-600 mb-8 sm:mb-10 font-bold text-base sm:text-lg leading-relaxed">
              약속드린 <strong className="text-blue-600">20% 할인 쿠폰</strong>이 발급되었습니다.<br />
              마이페이지에서 확인하실 수 있습니다.
            </p>
            <Button variant="primary" onClick={handleClose} className="w-full h-12 sm:h-14 rounded-2xl text-lg sm:text-xl font-black">
              확인
            </Button>
          </div>
        ) : (
          <div className="p-6 sm:p-12 flex flex-col">
            <div className="text-center mb-8 sm:mb-10">
              <div className="inline-flex items-center justify-center p-3 sm:p-4 bg-indigo-50 text-indigo-600 rounded-2xl mb-4 sm:mb-6">
                <Gift size={28} className="sm:w-8 sm:h-8" />
              </div>
              <h2 className="text-2xl sm:text-3xl font-black text-slate-800 mb-3">
                유니폴리 이용후기 작성
              </h2>
              <p className="text-slate-500 font-bold text-base sm:text-lg leading-relaxed">
                정성스러운 후기를 남겨주시면 결제 시 사용 가능한<br className="hidden sm:block" />
                <strong className="text-indigo-600"> 20% 할인 쿠폰</strong>을 즉시 지급해 드립니다.
              </p>
            </div>

            <div className="mb-6 sm:mb-8 flex justify-center gap-2 sm:gap-3">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setRating(star)}
                  onMouseEnter={() => setHoveredRating(star)}
                  onMouseLeave={() => setHoveredRating(0)}
                  className="transition-transform hover:scale-110 focus:outline-none"
                >
                  <Star
                    size={40}
                    className={`${
                      star <= (hoveredRating || rating)
                        ? 'fill-yellow-400 text-yellow-400'
                        : 'fill-slate-100 text-slate-200'
                    } transition-colors duration-200 sm:w-12 sm:h-12`}
                  />
                </button>
              ))}
            </div>

            <div className="mb-8">
              <textarea
                value={reviewText}
                onChange={(e) => setReviewText(e.target.value)}
                placeholder="유니폴리를 사용하시면서 느낀 점, 좋았던 기능, 개선했으면 하는 점 등을 자유롭게 적어주세요. (최소 10자 이상)"
                className="w-full h-40 p-5 border border-slate-200 rounded-2xl bg-slate-50 text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition-all resize-none font-bold text-base"
              />
            </div>

            <Button
              variant="primary"
              onClick={handleSubmit}
              disabled={isSubmitting || reviewText.trim().length < 10}
              className="w-full h-14 sm:h-16 rounded-[1.25rem] text-lg sm:text-xl font-black flex items-center justify-center gap-2 sm:gap-3 bg-indigo-600 hover:bg-indigo-700 active:scale-95 shadow-lg shadow-indigo-100"
            >
              {isSubmitting ? (
                <div className="w-6 h-6 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <Send size={18} className="sm:w-5 sm:h-5" />
                  쿠폰 받고 시작하기
                </>
              )}
            </Button>
          </div>
        )}
      </motion.div>
    </div>
  );
}
