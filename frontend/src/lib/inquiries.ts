import {
  isInquiryCategoryAllowedForType,
  type InquiryPayload,
  type InquiryResponse,
} from '@shared-contracts';
import { api } from './api';

export {
  BUG_REPORT_INQUIRY_CATEGORY_VALUES,
  INQUIRY_ALLOWED_CATEGORIES_BY_TYPE,
  INQUIRY_CATEGORY_VALUES,
  INQUIRY_TYPE_VALUES,
  INSTITUTION_TYPE_VALUES,
  ONE_TO_ONE_INQUIRY_CATEGORY_VALUES,
  PARTNERSHIP_INQUIRY_CATEGORY_VALUES,
  isInquiryCategoryAllowedForType,
} from '@shared-contracts';
export type {
  BugReportInquiryCategory,
  InquiryCategory,
  InquiryMetadataValue,
  InquiryPayload,
  InquiryResponse,
  InquiryType,
  InstitutionType,
  OneToOneInquiryCategory,
  PartnershipInquiryCategory,
} from '@shared-contracts';

export type InquiryErrors = Partial<Record<keyof InquiryPayload, string>>;

const emailPattern = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

function isBlank(value?: string) {
  return !value || !value.trim();
}

export function validateInquiry(payload: InquiryPayload): InquiryErrors {
  const errors: InquiryErrors = {};

  if (isBlank(payload.name)) {
    errors.name = payload.inquiry_type === 'bug_report' ? '?대쫫 ?먮뒗 ?됰꽕?꾩쓣 ?낅젰??二쇱꽭??' : '?대쫫???낅젰??二쇱꽭??';
  }
  if (isBlank(payload.email) || !emailPattern.test(payload.email.trim())) {
    errors.email = '?щ컮瑜??대찓??二쇱냼瑜??낅젰??二쇱꽭??';
  }
  if (isBlank(payload.message) || payload.message.trim().length < 10) {
    errors.message = '?댁슜? 10???댁긽 ?낅젰??二쇱꽭??';
  }

  if (payload.inquiry_type === 'one_to_one') {
    if (isBlank(payload.subject)) {
      errors.subject = '臾몄쓽 ?쒕ぉ???낅젰??二쇱꽭??';
    }
    if (!isInquiryCategoryAllowedForType('one_to_one', payload.inquiry_category)) {
      errors.inquiry_category = '臾몄쓽 ?좏삎???좏깮??二쇱꽭??';
    }
  }

  if (payload.inquiry_type === 'partnership') {
    if (isBlank(payload.institution_name)) {
      errors.institution_name = '湲곌?紐낆쓣 ?낅젰??二쇱꽭??';
    }
    if (isBlank(payload.phone)) {
      errors.phone = '?곕씫泥섎? ?낅젰??二쇱꽭??';
    }
    if (!payload.institution_type) {
      errors.institution_type = '湲곌? ?좏삎???좏깮??二쇱꽭??';
    }
    if (payload.inquiry_category && !isInquiryCategoryAllowedForType('partnership', payload.inquiry_category)) {
      errors.inquiry_category = '?묒뾽 臾몄쓽 ?좏삎??怨좎젙媛믪쑝濡??좏깮?⑤릺???⑸땲??';
    }
  }

  if (payload.inquiry_type === 'bug_report') {
    if (!isInquiryCategoryAllowedForType('bug_report', payload.inquiry_category)) {
      errors.inquiry_category = '踰꾧렇 ?먮뒗 湲곕뒫 ?쒖븞???좏깮??二쇱꽭??';
    }
    if (isBlank(payload.context_location)) {
      errors.context_location = '諛쒖깮 ?꾩튂瑜??낅젰??二쇱꽭??';
    }
  }

  return errors;
}

export async function submitInquiry(payload: InquiryPayload) {
  const normalized: InquiryPayload = {
    ...payload,
    name: payload.name?.trim(),
    email: payload.email.trim().toLowerCase(),
    phone: payload.phone?.trim(),
    subject: payload.subject?.trim(),
    message: payload.message.trim(),
    inquiry_category: payload.inquiry_type === 'partnership' ? 'partnership_request' : payload.inquiry_category,
    institution_name: payload.institution_name?.trim(),
    source_path: payload.source_path?.trim(),
    context_location: payload.context_location?.trim(),
    metadata: payload.metadata,
  };

  return api.post<InquiryResponse>('/api/v1/inquiries', normalized);
}
