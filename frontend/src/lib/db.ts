import { app, auth, firestoreDatabaseId, isFirebaseConfigured } from './firebase';
import type { UserProfile } from '@shared-contracts';
import { 
  collection, 
  doc, 
  getDoc, 
  getDocs, 
  setDoc, 
  updateDoc, 
  deleteDoc, 
  query, 
  where, 
  orderBy, 
  onSnapshot,
  serverTimestamp,
  Timestamp
} from 'firebase/firestore';
import { getFirestore, type Firestore } from 'firebase/firestore';

export enum OperationType {
  CREATE = 'create',
  UPDATE = 'update',
  DELETE = 'delete',
  LIST = 'list',
  GET = 'get',
  WRITE = 'write',
}

const db: Firestore | null =
  app && isFirebaseConfigured
    ? firestoreDatabaseId
      ? getFirestore(app, firestoreDatabaseId)
      : getFirestore(app)
    : null;

interface FirestoreErrorInfo {
  error: string;
  operationType: OperationType;
  path: string | null;
  authInfo: {
    userId?: string;
    email?: string | null;
    emailVerified?: boolean;
    isAnonymous?: boolean;
    tenantId?: string | null;
    providerInfo: {
      providerId: string;
      displayName: string | null;
      email: string | null;
      photoUrl: string | null;
    }[];
  }
}

export function handleFirestoreError(error: unknown, operationType: OperationType, path: string | null) {
  const errInfo: FirestoreErrorInfo = {
    error: error instanceof Error ? error.message : String(error),
    authInfo: {
      userId: auth?.currentUser?.uid,
      email: auth?.currentUser?.email,
      emailVerified: auth?.currentUser?.emailVerified,
      isAnonymous: auth?.currentUser?.isAnonymous,
      tenantId: auth?.currentUser?.tenantId,
      providerInfo: auth?.currentUser?.providerData.map(provider => ({
        providerId: provider.providerId,
        displayName: provider.displayName,
        email: provider.email,
        photoUrl: provider.photoURL
      })) || []
    },
    operationType,
    path
  }
  console.error('Firestore Error: ', JSON.stringify(errInfo));
  throw new Error(JSON.stringify(errInfo));
}

function requireFirestore() {
  if (!db || !isFirebaseConfigured) {
    throw new Error('Firebase is not configured for this environment.');
  }
  return db;
}

function optionalText(value: string | null | undefined, maxLen: number): string | undefined {
  const normalized = String(value ?? '').trim();
  if (!normalized) return undefined;
  return normalized.slice(0, maxLen);
}

function cleanStringList(values: string[] | null | undefined, maxItems: number, maxLen: number): string[] | undefined {
  if (!Array.isArray(values)) return undefined;
  const cleaned = values
    .map(value => optionalText(value, maxLen))
    .filter((value): value is string => Boolean(value));
  return cleaned.length ? cleaned.slice(0, maxItems) : undefined;
}

function compactPayload<T extends Record<string, unknown>>(payload: T): Partial<T> {
  return Object.fromEntries(
    Object.entries(payload).filter(([, value]) => value !== undefined),
  ) as Partial<T>;
}

export async function syncUserProfileToFirestore(profile: UserProfile): Promise<boolean> {
  const uid = optionalText(profile.firebase_uid, 128);
  const email = optionalText(profile.email, 320);
  if (!uid || !email || profile.is_guest) {
    return false;
  }

  const path = `users/${uid}`;
  try {
    const firestore = requireFirestore();
    const userRef = doc(firestore, 'users', uid);
    const existing = await getDoc(userRef);
    const payload = compactPayload({
      uid,
      email,
      displayName: optionalText(profile.name, 80),
      backendUserId: optionalText(profile.id, 128),
      grade: optionalText(profile.grade, 40),
      track: optionalText(profile.track, 80),
      career: optionalText(profile.career, 500),
      targetUniversity: optionalText(profile.target_university, 120),
      targetMajor: optionalText(profile.target_major, 120),
      admissionType: optionalText(profile.admission_type, 120),
      interestUniversities: cleanStringList(profile.interest_universities, 20, 120),
      marketingAgreed: Boolean(profile.marketing_agreed),
      updatedAt: serverTimestamp(),
    });

    if (existing.exists()) {
      await updateDoc(userRef, payload);
    } else {
      await setDoc(userRef, {
        ...payload,
        createdAt: serverTimestamp(),
      });
    }
    return true;
  } catch (error) {
    console.warn('Firestore profile sync skipped:', { path, error });
    return false;
  }
}

// User Profile
export async function getUserProfile(userId: string) {
  const path = `users/${userId}`;
  try {
    const docRef = doc(requireFirestore(), 'users', userId);
    const docSnap = await getDoc(docRef);
    return docSnap.exists() ? docSnap.data() : null;
  } catch (error) {
    handleFirestoreError(error, OperationType.GET, path);
  }
}

export async function createUserProfile(userId: string, data: any) {
  const path = `users/${userId}`;
  try {
    await setDoc(doc(requireFirestore(), 'users', userId), {
      ...data,
      uid: userId,
      createdAt: Timestamp.now(),
      updatedAt: Timestamp.now(),
    });
  } catch (error) {
    handleFirestoreError(error, OperationType.CREATE, path);
  }
}

export async function updateUserProfile(userId: string, data: any) {
  const path = `users/${userId}`;
  try {
    await updateDoc(doc(requireFirestore(), 'users', userId), {
      ...data,
      updatedAt: Timestamp.now(),
    });
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, path);
  }
}

// Documents
export async function getDocuments(userId: string) {
  const path = 'documents';
  try {
    const q = query(
      collection(requireFirestore(), 'documents'),
      where('userId', '==', userId),
      orderBy('createdAt', 'desc'),
    );
    const querySnapshot = await getDocs(q);
    return querySnapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
  } catch (error) {
    handleFirestoreError(error, OperationType.LIST, path);
  }
}

export async function createDocument(userId: string, data: any) {
  const path = 'documents';
  try {
    const newDocRef = doc(collection(requireFirestore(), 'documents'));
    await setDoc(newDocRef, {
      ...data,
      id: newDocRef.id,
      userId,
      createdAt: Timestamp.now(),
      updatedAt: Timestamp.now(),
    });
    return newDocRef.id;
  } catch (error) {
    handleFirestoreError(error, OperationType.CREATE, path);
  }
}

// Test Connection
export async function testConnection() {
  if (!db || !isFirebaseConfigured) {
    return;
  }
  try {
    await getDoc(doc(db, 'test', 'connection'));
  } catch (error) {
    if(error instanceof Error && error.message.includes('the client is offline')) {
      console.error("Please check your Firebase configuration. ");
    }
  }
}
