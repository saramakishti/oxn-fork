import { format } from 'date-fns';

export function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString);
    return format(date, 'yyyy-MM-dd HH:mm:ss');
  } catch (error) {
    console.error('Invalid date:', dateString);
    return dateString;
  }
}
