export const DISABLE_AUTH: boolean =
  process.env.NODE_ENV !== 'production' &&
  process.env.NEXT_PUBLIC_DISABLE_AUTH === 'true';

