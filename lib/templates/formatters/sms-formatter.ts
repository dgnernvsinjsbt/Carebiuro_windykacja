import { SMSValidator } from '../validators/sms-validator';
import type { FormattedSMS, TemplateData } from '../types';

/**
 * SMS Formatter
 * Formats SMS templates by replacing placeholders and validating content
 */

export class SMSFormatter {
  /**
   * Formats an SMS template with provided data
   */
  public static format(template: string, data: TemplateData): FormattedSMS {
    // Replace placeholders
    let text = template;
    Object.entries(data).forEach(([key, value]) => {
      const placeholder = `{{${key}}}`;
      text = text.replace(new RegExp(placeholder, 'g'), value || '');
    });

    // Validate formatted text
    const validator = new SMSValidator(text);
    const validation = validator.validate();

    return {
      text,
      length: validation.length,
      segments: validation.segments,
      encoding: validation.encoding,
      isValid: validation.isValid,
      warnings: validation.warnings,
    };
  }

  /**
   * Replaces placeholders without validation (for preview)
   */
  public static replacePlaceholders(
    template: string,
    data: TemplateData
  ): string {
    let text = template;
    Object.entries(data).forEach(([key, value]) => {
      const placeholder = `{{${key}}}`;
      text = text.replace(new RegExp(placeholder, 'g'), value || '');
    });
    return text;
  }

  /**
   * Gets list of placeholders in template
   */
  public static extractPlaceholders(template: string): string[] {
    const regex = /\{\{([^}]+)\}\}/g;
    const matches = Array.from(template.matchAll(regex));
    return matches.map((match) => match[1]);
  }

  /**
   * Validates template structure (checks for valid placeholder syntax)
   */
  public static validateTemplate(template: string): {
    isValid: boolean;
    errors: string[];
  } {
    const errors: string[] = [];

    // Check for unmatched braces
    const openBraces = (template.match(/\{\{/g) || []).length;
    const closeBraces = (template.match(/\}\}/g) || []).length;

    if (openBraces !== closeBraces) {
      errors.push('Niezamknięte placeholdery - sprawdź {{ i }}');
    }

    // Check for empty placeholders
    if (template.includes('{{}}')) {
      errors.push('Znaleziono puste placeholdery {{}}');
    }

    // Check for nested placeholders
    if (/\{\{[^}]*\{\{/.test(template)) {
      errors.push('Zagnieżdżone placeholdery są niedozwolone');
    }

    return {
      isValid: errors.length === 0,
      errors,
    };
  }

  /**
   * Sanitizes SMS text (removes invalid characters, normalizes whitespace)
   */
  public static sanitize(text: string): string {
    return (
      text
        // Normalize line breaks
        .replace(/\r\n/g, '\n')
        .replace(/\r/g, '\n')
        // Remove multiple spaces
        .replace(/ +/g, ' ')
        // Remove leading/trailing whitespace from lines
        .split('\n')
        .map((line) => line.trim())
        .join('\n')
        // Remove multiple consecutive newlines
        .replace(/\n{3,}/g, '\n\n')
        // Trim overall
        .trim()
    );
  }

  /**
   * Truncates SMS to fit within segment limit
   */
  public static truncate(text: string, maxSegments: number = 3): string {
    const validator = new SMSValidator(text);
    const validation = validator.validate();

    if (validation.segments <= maxSegments) {
      return text;
    }

    // Calculate max length for allowed segments
    const encoding = validation.encoding;
    const maxLength =
      encoding === 'GSM-7'
        ? maxSegments === 1
          ? 160
          : maxSegments * 153
        : maxSegments === 1
          ? 70
          : maxSegments * 67;

    // Truncate character by character to respect encoding
    let truncated = text;
    while (new SMSValidator(truncated).getLength() > maxLength) {
      truncated = truncated.slice(0, -1);
    }

    return truncated + '...';
  }

  /**
   * Estimates cost of SMS (in segments)
   */
  public static estimateCost(text: string): {
    segments: number;
    costMultiplier: number;
  } {
    const validator = new SMSValidator(text);
    const segments = validator.getSegments();

    return {
      segments,
      costMultiplier: segments,
    };
  }

  /**
   * Suggests optimizations for SMS text
   */
  public static suggestOptimizations(text: string): string[] {
    const suggestions: string[] = [];
    const validator = new SMSValidator(text);
    const validation = validator.validate();

    // Suggest removing UCS-2 characters if close to limit
    if (validation.encoding === 'UCS-2' && validation.segments > 1) {
      suggestions.push(
        'Rozważ usunięcie polskich znaków (ą→a, ę→e) aby zwiększyć limit do 160 znaków'
      );
    }

    // Suggest abbreviations if multi-segment
    if (validation.segments > 1) {
      if (text.includes('Szanowni Państwo')) {
        suggestions.push('Skróć "Szanowni Państwo" do "Szanowni P."');
      }
      if (text.includes('faktura')) {
        suggestions.push('Użyj "fakt." zamiast "faktura"');
      }
      if (text.includes('przypomnienie')) {
        suggestions.push('Użyj "przypom." zamiast "przypomnienie"');
      }
    }

    // Suggest removing extra whitespace
    if (/\s{2,}/.test(text)) {
      suggestions.push('Usuń podwójne spacje');
    }

    return suggestions;
  }
}
