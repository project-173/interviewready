import { ResumeLookupResult, ResumeSchema } from "@/types";

const TOKEN_PATTERN = /([^[.\]]+)|\[(\d+)\]/g;

const parseLocationTokens = (location: string): Array<string | number> => {
  const tokens: Array<string | number> = [];
  let match: RegExpExecArray | null;
  const matcher = new RegExp(TOKEN_PATTERN.source, "g");
  while ((match = matcher.exec(location)) !== null) {
    if (match[1]) tokens.push(match[1]);
    else if (match[2]) tokens.push(Number(match[2]));
  }
  return tokens;
};

const traverseResume = (
  resume: ResumeSchema,
  tokens: Array<string | number>,
): { value: unknown } | null => {
  let current: unknown = resume;
  for (const token of tokens) {
    if (typeof token === "string") {
      if (!current || typeof current !== "object" || !(token in current))
        return null;
      current = (current as Record<string, unknown>)[token];
    } else {
      if (!Array.isArray(current) || token < 0 || token >= current.length)
        return null;
      current = current[token];
    }
  }
  return current !== null && current !== undefined ? { value: current } : null;
};

const resolveDisplay = (
  value: unknown,
  tokens: Array<string | number>,
  topLevel: string | undefined,
): string | undefined => {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length ? trimmed : undefined;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    const stringItems = value.filter(
      (item): item is string => typeof item === "string" && !!item.trim(),
    );
    if (stringItems.length) return stringItems.join("; ");
    if (tokens.length === 1 && topLevel) return topLevel;
    return value.length ? JSON.stringify(value) : undefined;
  }
  if (typeof value === "object" && value !== null) {
    if (tokens.length === 1 && topLevel) return topLevel;
    const json = JSON.stringify(value);
    return json === "{}" ? undefined : json;
  }
  return undefined;
};

export const resolveResumeLocation = (
  resume: ResumeSchema | null | undefined,
  location: string | undefined,
): ResumeLookupResult => {
  if (!resume || !location || typeof location !== "string") {
    return { isValid: false };
  }

  const tokens = parseLocationTokens(location);
  if (!tokens.length) return { isValid: false };

  const topLevel = typeof tokens[0] === "string" ? tokens[0] : undefined;

  const result = traverseResume(resume, tokens);
  if (!result) return { isValid: false, topLevel };

  const display = resolveDisplay(result.value, tokens, topLevel);
  if (!display) return { isValid: false, topLevel };

  return {
    isValid: true,
    display,
    topLevel,
    usedSectionAsEvidence: tokens.length === 1 && display === topLevel,
  };
};
