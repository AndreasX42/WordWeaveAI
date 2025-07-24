export interface ValidationErrorInfo {
  issue?: string;
  detectedLanguage?: string;
  suggestions?: { word: string; language: string }[];
}
