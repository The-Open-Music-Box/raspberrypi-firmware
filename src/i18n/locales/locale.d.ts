declare module '*/locales/*.js' {
  const content: {
    [key: string]: string | {
      [key: string]: string | any;
    };
  };
  export default content;
}
