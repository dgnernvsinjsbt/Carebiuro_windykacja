/**
 * SMS Validator
 * Validates SMS message length, encoding, and segments
 *
 * GSM-7 encoding: 160 chars for single SMS, 153 chars per segment for multi-part
 * UCS-2 encoding (Polish chars): 70 chars for single SMS, 67 chars per segment
 */

export type SMSEncoding = 'GSM-7' | 'UCS-2';

export interface SMSValidationResult {
  length: number;
  encoding: SMSEncoding;
  segments: number;
  maxLength: number;
  isValid: boolean;
  warnings: string[];
}

export class SMSValidator {
  // GSM 7-bit character set (basic)
  // Includes standard ASCII, some European chars, and GSM extensions
  private static readonly GSM7_BASIC_CHARS =
    '@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1BÆæßÉ !"#¤%&\'()*+,-./0123456789:;<=>?' +
    '¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñü\àäö';

  // GSM 7-bit extended characters (count as 2 chars)
  private static readonly GSM7_EXTENDED_CHARS = '^{}\\[~]|€';

  // Max segments allowed
  private static readonly MAX_SEGMENTS = 3;

  constructor(private text: string) {}

  /**
   * Validates the SMS message and returns detailed info
   */
  public validate(): SMSValidationResult {
    const encoding = this.getEncoding();
    const length = this.getLength();
    const segments = this.getSegments();
    const maxLength = this.getMaxLength(encoding, segments);
    const isValid = segments <= SMSValidator.MAX_SEGMENTS;
    const warnings = this.getWarnings(encoding, segments, length);

    return {
      length,
      encoding,
      segments,
      maxLength,
      isValid,
      warnings,
    };
  }

  /**
   * Determines encoding based on character set
   */
  public getEncoding(): SMSEncoding {
    // Check if all characters are GSM-7 compatible
    for (const char of this.text) {
      if (
        !SMSValidator.GSM7_BASIC_CHARS.includes(char) &&
        !SMSValidator.GSM7_EXTENDED_CHARS.includes(char)
      ) {
        return 'UCS-2';
      }
    }
    return 'GSM-7';
  }

  /**
   * Calculates effective length (GSM extended chars count as 2)
   */
  public getLength(): number {
    const encoding = this.getEncoding();

    if (encoding === 'UCS-2') {
      return this.text.length;
    }

    // For GSM-7, extended chars count as 2
    let length = 0;
    for (const char of this.text) {
      if (SMSValidator.GSM7_EXTENDED_CHARS.includes(char)) {
        length += 2;
      } else {
        length += 1;
      }
    }
    return length;
  }

  /**
   * Calculates number of SMS segments
   */
  public getSegments(): number {
    const encoding = this.getEncoding();
    const length = this.getLength();

    if (encoding === 'GSM-7') {
      if (length === 0) return 0;
      if (length <= 160) return 1;
      return Math.ceil(length / 153);
    } else {
      // UCS-2
      if (length === 0) return 0;
      if (length <= 70) return 1;
      return Math.ceil(length / 67);
    }
  }

  /**
   * Gets maximum allowed length for current configuration
   */
  private getMaxLength(encoding: SMSEncoding, segments: number): number {
    if (segments === 0) return 0;

    if (encoding === 'GSM-7') {
      return segments === 1 ? 160 : segments * 153;
    } else {
      return segments === 1 ? 70 : segments * 67;
    }
  }

  /**
   * Generates warnings based on validation
   */
  private getWarnings(
    encoding: SMSEncoding,
    segments: number,
    length: number
  ): string[] {
    const warnings: string[] = [];

    // Polish characters warning
    if (encoding === 'UCS-2') {
      warnings.push(
        'Wiadomość zawiera polskie znaki (ą, ę, ć, etc.) - limit 70 znaków na SMS'
      );
    }

    // Multi-part SMS warning
    if (segments > 1 && segments <= SMSValidator.MAX_SEGMENTS) {
      warnings.push(
        `Wiadomość zostanie podzielona na ${segments} części (${this.formatSegmentInfo(encoding, segments)})`
      );
    }

    // Too long warning
    if (segments > SMSValidator.MAX_SEGMENTS) {
      warnings.push(
        `Wiadomość jest zbyt długa! Maksymalnie ${SMSValidator.MAX_SEGMENTS} segmenty (${this.getMaxLength(encoding, SMSValidator.MAX_SEGMENTS)} znaków)`
      );
    }

    // Cost warning for multi-part
    if (segments > 1) {
      warnings.push(`Koszt wysyłki: ${segments}× stawka za pojedynczego SMS`);
    }

    return warnings;
  }

  /**
   * Formats segment info for display
   */
  private formatSegmentInfo(encoding: SMSEncoding, segments: number): string {
    const charsPerSegment = encoding === 'GSM-7' ? 153 : 67;
    return `${charsPerSegment} znaków/segment`;
  }

  /**
   * Static helper: validates text without creating instance
   */
  public static validateText(text: string): SMSValidationResult {
    const validator = new SMSValidator(text);
    return validator.validate();
  }

  /**
   * Gets remaining characters until next segment
   */
  public getRemainingChars(): number {
    const encoding = this.getEncoding();
    const length = this.getLength();
    const segments = this.getSegments();

    if (segments === 0) {
      return encoding === 'GSM-7' ? 160 : 70;
    }

    const maxForCurrentSegments = this.getMaxLength(encoding, segments);
    return maxForCurrentSegments - length;
  }

  /**
   * Checks if adding more characters would create a new segment
   */
  public willCreateNewSegment(additionalChars: number): boolean {
    const currentSegments = this.getSegments();
    const newLength = this.getLength() + additionalChars;
    const encoding = this.getEncoding();

    let newSegments: number;
    if (encoding === 'GSM-7') {
      newSegments = newLength <= 160 ? 1 : Math.ceil(newLength / 153);
    } else {
      newSegments = newLength <= 70 ? 1 : Math.ceil(newLength / 67);
    }

    return newSegments > currentSegments;
  }
}
