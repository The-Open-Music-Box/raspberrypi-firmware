/**
 * Frontend Logger Utility
 * Provides structured logging with different levels and environment-based filtering
 */

enum LogLevel {
  ERROR = 0,
  WARN = 1,
  INFO = 2,
  DEBUG = 3
}

// LogEntry interface removed as it's not used in the current implementation

class Logger {
  private currentLevel: LogLevel;
  private isDevelopment: boolean;

  constructor() {
    this.isDevelopment = process.env.NODE_ENV === 'development';
    this.currentLevel = this.isDevelopment ? LogLevel.DEBUG : LogLevel.WARN;
  }

  private shouldLog(level: LogLevel): boolean {
    return level <= this.currentLevel;
  }

  private formatMessage(level: LogLevel, message: string, context?: string): string {
    const timestamp = new Date().toISOString();
    const levelName = LogLevel[level];
    const contextStr = context ? `[${context}] ` : '';
    return `${timestamp} ${levelName} ${contextStr}${message}`;
  }

  private log(level: LogLevel, message: string, data?: unknown, context?: string): void {
    if (!this.shouldLog(level)) return;

    const formattedMessage = this.formatMessage(level, message, context);

    switch (level) {
      case LogLevel.ERROR:
        if (data) {
          // eslint-disable-next-line no-console
          console.error(formattedMessage, data);
        } else {
          // eslint-disable-next-line no-console
          console.error(formattedMessage);
        }
        break;
      case LogLevel.WARN:
        if (data) {
          // eslint-disable-next-line no-console
          console.warn(formattedMessage, data);
        } else {
          // eslint-disable-next-line no-console
          console.warn(formattedMessage);
        }
        break;
      case LogLevel.INFO:
        if (data) {
          // eslint-disable-next-line no-console
          console.info(formattedMessage, data);
        } else {
          // eslint-disable-next-line no-console
          console.info(formattedMessage);
        }
        break;
      case LogLevel.DEBUG:
        if (data) {
          // eslint-disable-next-line no-console
          console.log(formattedMessage, data);
        } else {
          // eslint-disable-next-line no-console
          console.log(formattedMessage);
        }
        break;
    }
  }

  error(message: string, data?: unknown, context?: string): void {
    this.log(LogLevel.ERROR, message, data, context);
  }

  warn(message: string, data?: unknown, context?: string): void {
    this.log(LogLevel.WARN, message, data, context);
  }

  info(message: string, data?: unknown, context?: string): void {
    this.log(LogLevel.INFO, message, data, context);
  }

  debug(message: string, data?: unknown, context?: string): void {
    this.log(LogLevel.DEBUG, message, data, context);
  }
}

export const logger = new Logger();
export default logger;
