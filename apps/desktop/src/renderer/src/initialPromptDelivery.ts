export type InitialPromptRequest = Readonly<{
  id: string;
  prompt: string;
}>;

export type InitialPromptDeliveryResult = "delivered" | "pending";

let initialPromptRequestSeq = 0;

/**
 * A home-page prompt is a durable request within the mounted work session.
 * Its identity must not depend on the work path: importing/renaming a work can
 * change that path while the same request is still being delivered.
 */
export function createInitialPromptRequest(
  prompt: string,
  now = Date.now(),
): InitialPromptRequest {
  initialPromptRequestSeq += 1;
  return {
    id: `home-prompt-${now.toString(36)}-${initialPromptRequestSeq.toString(36)}`,
    prompt,
  };
}

/**
 * The only completion definition for a launch prompt is an acknowledged CLI
 * launch outcome (stable live process or a successful immediate exit).
 * Failed/throwing attempts stay pending and may be retried.
 */
export async function deliverInitialPrompt(
  request: InitialPromptRequest,
  launch: (prompt: string) => Promise<boolean>,
): Promise<InitialPromptDeliveryResult> {
  try {
    return await launch(request.prompt) ? "delivered" : "pending";
  } catch {
    return "pending";
  }
}

/** A late acknowledgement may consume only the request it launched. */
export function consumeInitialPromptRequest(
  request: InitialPromptRequest | undefined,
  deliveredRequestId: string,
): InitialPromptRequest | undefined {
  return request?.id === deliveredRequestId ? undefined : request;
}

export function consumeInitialPromptFromWork<
  T extends { initialPrompt?: InitialPromptRequest },
>(work: T, deliveredRequestId: string): T {
  const initialPrompt = consumeInitialPromptRequest(work.initialPrompt, deliveredRequestId);
  return initialPrompt === work.initialPrompt ? work : { ...work, initialPrompt };
}
