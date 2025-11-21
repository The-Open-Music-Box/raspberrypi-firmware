interface Crypto {
  randomUUID(): string;
  getRandomValues(array: TypedArray): TypedArray;
  subtle: SubtleCrypto;
} 