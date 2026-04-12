import React, { useEffect, useMemo, useState } from 'react';
import { School } from 'lucide-react';
import { cn } from '../lib/cn';
import { resolveApiBaseUrl } from '../lib/api';
import universityLogoManifest from '../data/university-logo-manifest.json';

interface UniversityLogoProps {
  universityName: string;
  className?: string;
  alt?: string;
  fallbackClassName?: string;
  textFallbackClassName?: string;
}

function normalizeUniversityName(name: string | null | undefined) {
  if (!name) return '';
  return name
    .trim()
    .replace(/\(.*?\)/g, '')
    .replace(/\[.*?\]/g, '')
    .replace(/\s+/g, '')
    .replace(/[^\p{L}\p{N}]/gu, '')
    .toLowerCase();
}

function resolveLocalLogoFilename(universityName: string) {
  const manifest = universityLogoManifest as Record<string, string>;
  const normalized = normalizeUniversityName(universityName);
  if (!normalized) return null;

  const exact = manifest[normalized];
  if (exact) return exact;

  const keys = Object.keys(manifest);
  for (const key of keys) {
    if (normalized.startsWith(key) || key.startsWith(normalized)) {
      return manifest[key];
    }
  }

  return null;
}

const UNIVERSITY_DOMAIN_MAP = new Map<string, string>(
  [
    ['서울대학교', 'snu.ac.kr'],
    ['연세대학교', 'yonsei.ac.kr'],
    ['고려대학교', 'korea.ac.kr'],
    ['서강대학교', 'sogang.ac.kr'],
    ['성균관대학교', 'skku.edu'],
    ['한양대학교', 'hanyang.ac.kr'],
    ['중앙대학교', 'cau.ac.kr'],
    ['경희대학교', 'khu.ac.kr'],
    ['한국외국어대학교', 'hufs.ac.kr'],
    ['이화여자대학교', 'ewha.ac.kr'],
    ['숙명여자대학교', 'sm.ac.kr'],
    ['건국대학교', 'konkuk.ac.kr'],
    ['동국대학교', 'dongguk.edu'],
    ['홍익대학교', 'hongik.ac.kr'],
    ['숭실대학교', 'soongsil.ac.kr'],
    ['국민대학교', 'kookmin.ac.kr'],
    ['세종대학교', 'sejong.ac.kr'],
    ['단국대학교', 'dankook.ac.kr'],
    ['아주대학교', 'ajou.ac.kr'],
    ['인하대학교', 'inha.ac.kr'],
    ['광운대학교', 'kw.ac.kr'],
    ['가천대학교', 'gachon.ac.kr'],
    ['서울시립대학교', 'uos.ac.kr'],
    ['부산대학교', 'pusan.ac.kr'],
    ['경북대학교', 'knu.ac.kr'],
    ['전남대학교', 'jnu.ac.kr'],
    ['전북대학교', 'jbnu.ac.kr'],
    ['충남대학교', 'cnu.ac.kr'],
    ['충북대학교', 'cbnu.ac.kr'],
    ['강원대학교', 'kangwon.ac.kr'],
    ['제주대학교', 'jejunu.ac.kr'],
    ['영남대학교', 'yu.ac.kr'],
    ['계명대학교', 'kmu.ac.kr'],
    ['울산대학교', 'ulsan.ac.kr'],
    ['부경대학교', 'pknu.ac.kr'],
    ['서울과학기술대학교', 'seoultech.ac.kr'],
    ['인천대학교', 'inu.ac.kr'],
    ['경기대학교', 'kyonggi.ac.kr'],
    ['명지대학교', 'mju.ac.kr'],
    ['상명대학교', 'smu.ac.kr'],
    ['한성대학교', 'hansung.ac.kr'],
    ['포항공과대학교', 'postech.ac.kr'],
    ['한국과학기술원', 'kaist.ac.kr'],
    ['울산과학기술원', 'unist.ac.kr'],
    ['대구경북과학기술원', 'dgist.ac.kr'],
    ['광주과학기술원', 'gist.ac.kr'],
  ].map(([name, domain]) => [normalizeUniversityName(name), domain]),
);

function resolveUniversityDomain(universityName: string) {
  const normalized = normalizeUniversityName(universityName);
  if (!normalized) return null;

  const exact = UNIVERSITY_DOMAIN_MAP.get(normalized);
  if (exact) return exact;

  for (const [key, domain] of UNIVERSITY_DOMAIN_MAP.entries()) {
    if (normalized.startsWith(key) || key.startsWith(normalized)) {
      return domain;
    }
  }

  return null;
}

function buildUniversityLogoCandidates(universityName: string | null | undefined) {
  const name = (universityName || '').trim();
  if (!name) return [];

  const localFilename = resolveLocalLogoFilename(name);
  const localUrl = localFilename ? `/university-logos/${encodeURIComponent(localFilename)}` : null;

  const encoded = encodeURIComponent(name);
  const apiBaseUrl = resolveApiBaseUrl();
  const candidates = [localUrl, `${apiBaseUrl}/api/v1/assets/univ-logo?name=${encoded}`].filter(
    (value): value is string => Boolean(value),
  );

  const mappedDomain = resolveUniversityDomain(name);
  if (mappedDomain) {
    candidates.push(`https://logo.clearbit.com/${mappedDomain}`);
    candidates.push(`https://www.google.com/s2/favicons?domain=${mappedDomain}&sz=128`);
  }

  return Array.from(new Set(candidates));
}

function getFallbackText(universityName: string | null | undefined) {
  const trimmed = (universityName || '').trim();
  if (!trimmed) return '';
  return trimmed.slice(0, 1);
}

export function UniversityLogo({
  universityName,
  className,
  alt,
  fallbackClassName,
  textFallbackClassName,
}: UniversityLogoProps) {
  const candidates = useMemo(() => buildUniversityLogoCandidates(universityName), [universityName]);
  const [candidateIndex, setCandidateIndex] = useState(0);

  useEffect(() => {
    setCandidateIndex(0);
  }, [universityName]);

  const src = candidates[candidateIndex];

  if (src) {
    return (
      <img
        src={src}
        className={className}
        alt={alt ?? `${universityName} 로고`}
        referrerPolicy="no-referrer"
        loading="lazy"
        onError={() => {
          setCandidateIndex(previous => previous + 1);
        }}
      />
    );
  }

  const fallbackText = getFallbackText(universityName);

  return (
    <div className={cn('flex items-center justify-center', className, fallbackClassName)}>
      {fallbackText ? (
        <span className={cn('text-xs font-black text-slate-700', textFallbackClassName)}>{fallbackText}</span>
      ) : (
        <School size={14} className="text-slate-500" />
      )}
    </div>
  );
}
