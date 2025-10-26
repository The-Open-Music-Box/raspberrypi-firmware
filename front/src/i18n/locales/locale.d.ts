declare module '*/locales/*.js' {
  const content: {
    [key: string]: string | {
      [key: string]: string | unknown;
    };
  };
  export default content;
}
