import { beforeEach, describe, expect, it, vi } from 'vitest';
import { backendService, formatInterviewCoachPayload } from '../backendService.ts';

describe('backendService interview coach flow', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    global.fetch = vi.fn();
  });

  it('formats structured interview questions into readable chat copy', () => {
    const formatted = formatInterviewCoachPayload({
      current_question_number: 2,
      total_questions: 5,
      question: 'Tell me about a time you learned a new framework quickly.',
      feedback: 'Your previous answer was too generic.',
      answer_score: 42,
      tip: 'Use a concrete example with measurable impact.',
      next_challenge: 'Be more specific about your actions.',
    });

    expect(formatted).toContain('Question 2 of 5');
    expect(formatted).toContain('Your previous answer was too generic.');
    expect(formatted).toContain('Score: 42/100');
    expect(formatted).toContain('Tip: Use a concrete example with measurable impact.');
  });

  it('starts the interview from the backend instead of a hardcoded frontend prompt', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({
        payload: {
          current_question_number: 1,
          total_questions: 5,
          question: 'Walk me through a project that best matches this role.',
          feedback: '',
          tip: 'Use STAR.',
          can_proceed: true,
        },
      }),
    });

    const responseText = await backendService.interviewCoachAgent(
      {
        work: [{ name: 'Example Co', position: 'Engineer' }],
        education: [],
        awards: [],
        certificates: [],
        skills: [{ name: 'React' }],
        projects: [],
      },
      'Frontend engineer role',
      [],
    );

    expect(global.fetch).toHaveBeenCalledTimes(1);
    const [, requestInit] = global.fetch.mock.calls[0];
    const body = JSON.parse(requestInit.body);

    expect(body.intent).toBe('INTERVIEW_COACH');
    expect(body.jobDescription).toBe('Frontend engineer role');
    expect(body.messageHistory).toEqual([]);
    expect(responseText).toContain('Question 1 of 5');
    expect(responseText).toContain('Walk me through a project that best matches this role.');
  });
});
