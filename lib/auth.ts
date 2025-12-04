import { SignJWT, jwtVerify } from 'jose';

// Hardcoded credentials (na start, później można przenieść do env)
export const ADMIN_CREDENTIALS = {
  login: 'admin',
  password: 'web140569X$',
};

// Secret do podpisywania JWT (fallback jeśli nie ma w env)
const getSecret = () => {
  const secret = process.env.JWT_SECRET || 'carebiuro-windykacja-secret-key-2025';
  return new TextEncoder().encode(secret);
};

// Interfejs dla payload JWT
export interface JWTPayload {
  login: string;
  iat: number;
  exp: number;
}

/**
 * Generuje JWT token dla zalogowanego użytkownika
 * Token ważny przez 7 dni
 */
export async function signToken(login: string): Promise<string> {
  const secret = getSecret();

  const token = await new SignJWT({ login })
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setExpirationTime('7d') // 7 dni ważności
    .sign(secret);

  return token;
}

/**
 * Weryfikuje JWT token i zwraca payload
 * Rzuca błąd jeśli token nieważny
 */
export async function verifyToken(token: string): Promise<JWTPayload> {
  try {
    const secret = getSecret();
    const { payload } = await jwtVerify(token, secret);

    return {
      login: payload.login as string,
      iat: payload.iat as number,
      exp: payload.exp as number,
    };
  } catch (error) {
    throw new Error('Invalid token');
  }
}

/**
 * Sprawdza czy podane credentials są poprawne
 */
export function validateCredentials(login: string, password: string): boolean {
  return login === ADMIN_CREDENTIALS.login && password === ADMIN_CREDENTIALS.password;
}
