import express, { type Request, type Response } from "express";
import { writeFile } from "node:fs/promises";
import { createAgentSession, ModelRuntime, SessionManager } from "@earendil-works/pi-coding-agent";

const app = express();
app.use(express.json({ limit: "128kb" }));

type Provider = "ollama" | "anthropic" | "openai";

const OLLAMA_MODELS_PATH = "/tmp/lenny-lens-ollama-models.json";

async function createModelRuntime(provider: Provider, model: string): Promise<ModelRuntime> {
  if (provider !== "ollama") {
    return ModelRuntime.create();
  }

  // Pi 0.87 reads models.json literally and does not expand ${ENV_VAR} values.
  // Materialise its OpenAI-compatible Ollama provider configuration at runtime
  // so Compose or a .env file can safely control the native Windows endpoint.
  const baseUrl = `${(process.env.OLLAMA_BASE_URL ?? "http://host.docker.internal:11434").replace(/\/+$/, "")}/v1`;
  await writeFile(
    OLLAMA_MODELS_PATH,
    JSON.stringify({
      providers: {
        ollama: {
          baseUrl,
          api: "openai-completions",
          apiKey: "ollama",
          models: [{ id: model, contextWindow: 32768, maxTokens: 768, input: ["text"], reasoning: false }],
        },
      },
    }),
  );
  return ModelRuntime.create({ modelsPath: OLLAMA_MODELS_PATH });
}

function badRequest(response: Response, message: string) {
  return response.status(400).json({ error: { code: "INVALID_AGENT_REQUEST", message } });
}

app.get("/health", async (_request, response) => {
  response.json({ status: "ok", tools: [], runtime: "pi-coding-agent-sdk" });
});

app.post("/generate", async (request: Request, response: Response) => {
  const { provider, model, prompt } = request.body as { provider?: Provider; model?: string; prompt?: string };
  if (!provider || !model || !prompt || typeof prompt !== "string") {
    return badRequest(response, "provider, model, and prompt are required.");
  }
  if (!["ollama", "anthropic", "openai"].includes(provider)) {
    return badRequest(response, "Unsupported provider.");
  }

  try {
    const modelRuntime = await createModelRuntime(provider, model);
    const selectedModel = modelRuntime.getModel(provider, model);
    if (!selectedModel) {
      return response.status(503).json({ error: { code: "MODEL_UNAVAILABLE", message: `Pi cannot find ${provider}/${model}. Check provider configuration.` } });
    }
    // Deliberately expose no read, write, shell, or network tools. The FastAPI
    // service owns retrieval; this agent only synthesizes explicitly supplied evidence.
    const { session } = await createAgentSession({
      model: selectedModel,
      modelRuntime,
      tools: [],
      sessionManager: SessionManager.inMemory(),
      thinkingLevel: "off",
      cwd: "/tmp/lenny-lens-agent",
    });
    try {
      await session.prompt(prompt);
      const content = session.getLastAssistantText();
      response.json({ content, provider, model });
    } finally {
      session.dispose();
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : "Pi agent failed without a message.";
    response.status(503).json({ error: { code: "AGENT_UNAVAILABLE", message } });
  }
});

const port = Number(process.env.PORT ?? "3001");
app.listen(port, "0.0.0.0", () => {
  console.log(JSON.stringify({ event: "agent_runtime_started", port, tools: [] }));
});
