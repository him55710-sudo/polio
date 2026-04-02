import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Building2, CheckCircle2, MessageSquare } from 'lucide-react';
import toast from 'react-hot-toast';
import type { InstitutionType } from '@shared-contracts';
import { useAuth } from '../contexts/AuthContext';
import { useAuthStore } from '../store/authStore';
import { submitInquiry, type InquiryErrors, type InquiryPayload, validateInquiry } from '../lib/inquiries';
import { Badge, Button, Dialog, DialogBody, DialogHeader, DialogPanel, Input, TextArea } from './ui';

interface B2BPartnershipModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const initialForm: InquiryPayload = {
  inquiry_type: 'partnership',
  inquiry_category: 'partnership_request',
  institution_name: '',
  name: '',
  phone: '',
  email: '',
  institution_type: 'school',
  message: '',
  source_path: '/app?source=partnership-modal',
  metadata: {
    entry_point: 'app_partnership_modal',
  },
};

export function B2BPartnershipModal({ isOpen, onClose }: B2BPartnershipModalProps) {
  const authUser = useAuth().user;
  const dbUser = useAuthStore(state => state.user);
  const [form, setForm] = useState<InquiryPayload>(initialForm);
  const [errors, setErrors] = useState<InquiryErrors>({});
  const [submitted, setSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!isOpen) return;

    setSubmitted(false);
    setErrors({});
    setForm({
      ...initialForm,
      name: dbUser?.name || authUser?.displayName || '',
      email: dbUser?.email || authUser?.email || '',
    });
  }, [authUser?.displayName, authUser?.email, dbUser?.email, dbUser?.name, isOpen]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const validation = validateInquiry(form);
    setErrors(validation);

    if (Object.keys(validation).length > 0) {
      toast.error('필수 정보를 확인해주세요.');
      return;
    }

    setIsSubmitting(true);
    const loadingId = toast.loading('문의를 접수하고 있습니다...');

    try {
      await submitInquiry(form);
      setSubmitted(true);
      setErrors({});
      toast.success('문의가 접수되었습니다. 남겨주신 연락처로 안내드릴게요.', { id: loadingId });
    } catch (error) {
      console.error('Partnership inquiry failed:', error);
      toast.error('문의 접수에 실패했습니다. 잠시 후 다시 시도해주세요.', { id: loadingId });
    } finally {
      setIsSubmitting(false);
    }
  };

  const closeModal = () => {
    setSubmitted(false);
    setErrors({});
    onClose();
  };

  return (
    <Dialog open={isOpen} onClose={closeModal}>
      <DialogPanel size="lg">
        {!submitted ? (
          <>
            <DialogHeader
              title="학교·학원 협업 문의"
              description="앱 안에서도 바로 문의를 남길 수 있도록 간단한 접수 폼을 제공합니다."
              onClose={closeModal}
            />
            <DialogBody>
              <div className="mb-5 flex items-center gap-3 rounded-2xl border border-blue-100 bg-blue-50 p-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white text-blue-600">
                  <Building2 size={18} />
                </div>
                <div>
                  <p className="text-sm font-bold text-slate-800">Partnership Contact</p>
                  <p className="text-xs font-medium text-slate-500">기관/운영 문의를 빠르게 접수한 뒤 상세 상담으로 연결합니다.</p>
                </div>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <Input
                    id="partnership-org"
                    label="기관명"
                    value={form.institution_name ?? ''}
                    onChange={event => setForm(prev => ({ ...prev, institution_name: event.target.value }))}
                    error={errors.institution_name}
                    required
                  />
                  <Input
                    id="partnership-name"
                    label="담당자명"
                    value={form.name ?? ''}
                    onChange={event => setForm(prev => ({ ...prev, name: event.target.value }))}
                    error={errors.name}
                    required
                  />
                  <Input
                    id="partnership-phone"
                    label="연락처"
                    value={form.phone ?? ''}
                    onChange={event => setForm(prev => ({ ...prev, phone: event.target.value }))}
                    error={errors.phone}
                    required
                  />
                  <Input
                    id="partnership-email"
                    type="email"
                    label="이메일"
                    value={form.email}
                    onChange={event => setForm(prev => ({ ...prev, email: event.target.value }))}
                    error={errors.email}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <label htmlFor="partnership-type" className="block text-sm font-bold text-slate-700">
                    기관 유형
                  </label>
                  <select
                    id="partnership-type"
                    value={form.institution_type ?? 'school'}
                    onChange={event => setForm(prev => ({ ...prev, institution_type: event.target.value as InstitutionType }))}
                    className="h-11 w-full rounded-2xl border border-slate-300 bg-white px-3.5 text-sm font-medium text-slate-700 outline-none focus-visible:ring-2 focus-visible:ring-blue-300"
                  >
                    <option value="school">학교</option>
                    <option value="academy">학원</option>
                    <option value="other">기타</option>
                  </select>
                  {errors.institution_type ? <p className="text-xs font-semibold text-red-600">{errors.institution_type}</p> : null}
                </div>

                <TextArea
                  id="partnership-message"
                  label="문의 내용"
                  value={form.message}
                  onChange={event => setForm(prev => ({ ...prev, message: event.target.value }))}
                  error={errors.message}
                  placeholder="운영 상황, 도입 목표, 적용 범위를 적어주세요."
                  required
                />

                <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                  <Link to="/contact?type=partnership" onClick={closeModal} className="text-sm font-semibold text-blue-700 hover:text-blue-800">
                    문의 페이지에서 자세히 작성하기
                  </Link>
                  <Button type="submit" variant="primary" disabled={isSubmitting}>
                    <MessageSquare size={16} />
                    {isSubmitting ? '접수 중...' : '문의 보내기'}
                  </Button>
                </div>
              </form>
            </DialogBody>
          </>
        ) : (
          <>
            <DialogHeader title="문의 접수 완료" description="등록된 연락처로 확인 후 안내드리겠습니다." onClose={closeModal} />
            <DialogBody>
              <div className="flex flex-col items-center justify-center gap-4 py-6 text-center">
                <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
                  <CheckCircle2 size={28} />
                </div>
                <Badge tone="success">Received</Badge>
                <p className="max-w-md text-sm font-medium leading-6 text-slate-500">
                  문의 내용이 안전하게 접수되었습니다. 필요하면 문의 페이지에서 추가 자료를 남길 수 있습니다.
                </p>
                <div className="mt-2 flex flex-wrap items-center justify-center gap-2">
                  <Link to="/contact?type=partnership" onClick={closeModal}>
                    <Button variant="secondary">문의 페이지 보기</Button>
                  </Link>
                  <Button variant="primary" onClick={closeModal}>
                    닫기
                  </Button>
                </div>
              </div>
            </DialogBody>
          </>
        )}
      </DialogPanel>
    </Dialog>
  );
}

