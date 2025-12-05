import type { AudioValidationResult } from '../types/audio.types';
import { MAX_FILE_SIZE_MB, SUPPORTED_FORMATS } from './constants';

export function validateAudioFile(
  file: File,
  maxSizeMB: number = MAX_FILE_SIZE_MB
): AudioValidationResult {
  const result: AudioValidationResult = { isValid: true };

  if (file.size > maxSizeMB * 1024 * 1024) {
    result.isValid = false;
    result.error = `File size exceeds ${maxSizeMB}MB limit`;
    return result;
  }

  const extension = file.name.split('.').pop()?.toLowerCase();
  if (!extension || !SUPPORTED_FORMATS.includes(extension)) {
    result.isValid = false;
    result.error = `Unsupported format. Accepted: ${SUPPORTED_FORMATS.join(', ')}`;
    return result;
  }

  if (file.size > 50 * 1024 * 1024) {
    result.warnings = result.warnings || [];
    result.warnings.push('Large file size may take longer to process');
  }

  return result;
}
