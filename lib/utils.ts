/**
 * Utility function for conditional className joining
 * Similar to clsx/classnames
 */
export function cn(...classes: (string | undefined | false | null | Record<string, boolean>)[]): string {
  return classes
    .map((cls) => {
      if (typeof cls === 'object' && cls !== null) {
        // Handle conditional object: { 'class-name': true, 'other': false }
        return Object.entries(cls)
          .filter(([, value]) => value)
          .map(([key]) => key)
          .join(' ');
      }
      return cls;
    })
    .filter(Boolean)
    .join(' ');
}
