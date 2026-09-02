import assert from "node:assert/strict";
import test from "node:test";
import { localCodexModelDefinitions } from "../src/catalog/runtimeModels";

test("local Codex access keeps the real model slug", () => {
  const [model] = localCodexModelDefinitions([{
    id: "gpt-5.6-sol",
    name: "GPT-5.6-Sol",
    description: "Frontier",
  }]);

  assert.equal(model?.id, "gpt-5.6-sol");
  assert.equal(model?.modelId, "gpt-5.6-sol");
  assert.equal(model?.modality, "text");
  assert.match(model?.provider ?? "", /Codex/);
  assert.equal("executor" in (model ?? {}), false);
})
