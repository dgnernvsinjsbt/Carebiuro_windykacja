export interface FAQ {
  id: number;
  question: string;
  answer: string;
  keywords: string[];
}

/**
 * Normalize text for matching: lowercase, remove Polish diacritics, trim
 */
function normalizeText(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '') // Remove diacritics
    .trim();
}

/**
 * Calculate simple Levenshtein distance between two strings
 * Used for fuzzy matching
 */
function levenshteinDistance(str1: string, str2: string): number {
  const len1 = str1.length;
  const len2 = str2.length;
  const matrix: number[][] = [];

  // Initialize matrix
  for (let i = 0; i <= len1; i++) {
    matrix[i] = [i];
  }
  for (let j = 0; j <= len2; j++) {
    matrix[0][j] = j;
  }

  // Fill matrix
  for (let i = 1; i <= len1; i++) {
    for (let j = 1; j <= len2; j++) {
      if (str1[i - 1] === str2[j - 1]) {
        matrix[i][j] = matrix[i - 1][j - 1];
      } else {
        matrix[i][j] = Math.min(
          matrix[i - 1][j - 1] + 1, // substitution
          matrix[i][j - 1] + 1,     // insertion
          matrix[i - 1][j] + 1      // deletion
        );
      }
    }
  }

  return matrix[len1][len2];
}

/**
 * Calculate similarity score (0-1) based on Levenshtein distance
 */
function calculateSimilarity(str1: string, str2: string): number {
  const distance = levenshteinDistance(str1, str2);
  const maxLength = Math.max(str1.length, str2.length);
  return maxLength === 0 ? 1 : 1 - distance / maxLength;
}

/**
 * Find FAQ match based on user message
 * Returns the best matching FAQ or null if no good match found
 */
export function findFAQMatch(
  userMessage: string,
  faqs: FAQ[],
  threshold: number = 0.6
): FAQ | null {
  const normalizedMessage = normalizeText(userMessage);
  const messageWords = normalizedMessage.split(/\s+/);

  let bestMatch: { faq: FAQ; score: number } | null = null;

  for (const faq of faqs) {
    let score = 0;

    // Check exact keyword matches (highest priority)
    for (const keyword of faq.keywords) {
      const normalizedKeyword = normalizeText(keyword);

      // Exact match in message
      if (normalizedMessage.includes(normalizedKeyword)) {
        score += 3;
      }

      // Word-level match
      for (const word of messageWords) {
        if (word === normalizedKeyword) {
          score += 2;
        }
      }

      // Fuzzy match for keywords
      for (const word of messageWords) {
        const similarity = calculateSimilarity(word, normalizedKeyword);
        if (similarity > 0.8) {
          score += similarity * 1.5;
        }
      }
    }

    // Check similarity with question
    const normalizedQuestion = normalizeText(faq.question);
    const questionWords = normalizedQuestion.split(/\s+/);

    for (const messageWord of messageWords) {
      for (const questionWord of questionWords) {
        if (messageWord.length > 3 && questionWord.length > 3) {
          const similarity = calculateSimilarity(messageWord, questionWord);
          if (similarity > 0.85) {
            score += similarity * 0.5;
          }
        }
      }
    }

    // Normalize score by number of keywords
    const normalizedScore = score / Math.max(faq.keywords.length, 1);

    if (normalizedScore > threshold && (!bestMatch || normalizedScore > bestMatch.score)) {
      bestMatch = { faq, score: normalizedScore };
    }
  }

  return bestMatch?.faq || null;
}

/**
 * Get all FAQs as formatted context for OpenAI
 */
export function getFAQContext(faqs: FAQ[]): string {
  return faqs
    .map((faq) => `Pytanie: ${faq.question}\nOdpowiedź: ${faq.answer}`)
    .join('\n\n');
}
