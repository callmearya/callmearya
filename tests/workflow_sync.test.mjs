import { test, describe } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { updateReadmeCacheBuster } from "../generate.mjs";

const REPO_ROOT = path.resolve(import.meta.dirname, "..");

describe("TDD: GitHub Actions Workflow & Sync Integrity", () => {
  const workflowPath = path.join(REPO_ROOT, ".github", "workflows", "jet-heatmap.yml");
  const gitignorePath = path.join(REPO_ROOT, ".gitignore");
  const readmePath = path.join(REPO_ROOT, "README.md");

  test("should have a valid jet-heatmap.yml workflow file", () => {
    assert.ok(fs.existsSync(workflowPath), "jet-heatmap.yml must exist");
    const content = fs.readFileSync(workflowPath, "utf8");
    assert.match(content, /name:\s*Update jet heatmap SVG/i);
    assert.match(content, /schedule:/);
    assert.match(content, /workflow_dispatch:/);
    assert.match(content, /permissions:\s*\n\s*contents:\s*write/);
  });

  test("should schedule runs at midnight (00:00 IST / 00:00 UTC)", () => {
    const content = fs.readFileSync(workflowPath, "utf8");
    const hasMidnightSchedule = /cron:\s*"(?:30 18 \* \* \*|0 0 \* \* \*)"/.test(content);
    assert.ok(hasMidnightSchedule, "Workflow must be scheduled at midnight");
  });

  test("should ensure file_pattern does NOT stage gitignored paths like dist/", () => {
    const workflowContent = fs.readFileSync(workflowPath, "utf8");
    const gitignoreContent = fs.existsSync(gitignorePath) ? fs.readFileSync(gitignorePath, "utf8") : "";

    const filePatternMatch = workflowContent.match(/file_pattern:\s*"?([^"\n]+)"?/);
    assert.ok(filePatternMatch, "file_pattern must be specified");
    const stagedPatterns = filePatternMatch[1].split(/\s+/).filter(Boolean);

    if (/^dist\/?$/m.test(gitignoreContent)) {
      for (const pattern of stagedPatterns) {
        assert.ok(
          !pattern.startsWith("dist/"),
          `file_pattern contains gitignored path '${pattern}', which causes git add exit code 1 failure`
        );
      }
    }
  });

  test("should reference a valid cache-busting version on github-jet.svg in README.md", () => {
    assert.ok(fs.existsSync(readmePath), "README.md must exist");
    const readmeContent = fs.readFileSync(readmePath, "utf8");
    assert.match(readmeContent, /github-jet\.svg\?v=\d+/, "README.md should include a versioned cache-buster query parameter");
  });

  test("should correctly update README.md cache buster timestamp via updateReadmeCacheBuster()", () => {
    assert.ok(typeof updateReadmeCacheBuster === "function", "updateReadmeCacheBuster must be exported from generate.mjs");
    const testTs = "1799999999";
    const updatedContent = updateReadmeCacheBuster(testTs, false);
    assert.match(updatedContent, new RegExp(`github-jet\\.svg\\?v=${testTs}`), "README content must include the new timestamp");
    assert.match(updatedContent, /dark\.svg\?v=17/, "Must preserve dark.svg parameters");
    assert.match(updatedContent, /light\.svg\?v=17/, "Must preserve light.svg parameters");
  });
});

describe("Security: STRIDE & OWASP Workflow Hardening Suite", () => {
  const workflowPath = path.join(REPO_ROOT, ".github", "workflows", "jet-heatmap.yml");

  test("OWASP A05: Token least-privilege configuration", () => {
    const content = fs.readFileSync(workflowPath, "utf8");
    assert.match(content, /contents:\s*write/, "Workflow requires contents: write for committing");
    assert.doesNotMatch(content, /id-token:\s*write/, "Should not request excessive OIDC permissions");
    assert.doesNotMatch(content, /pull-requests:\s*write/, "Should not request PR write permissions");
  });

  test("STRIDE Tampering: Environment variable command injection defense", () => {
    const content = fs.readFileSync(workflowPath, "utf8");
    assert.match(content, /env:\s*\n\s*GH_USERNAME:\s*\${{\s*github\.repository_owner\s*}}/, "GH_USERNAME must be securely mapped to env");
    assert.match(content, /run:\s*node generate\.mjs/, "Run step must invoke safe node entrypoint without shell interpolation");
  });

  test("STRIDE Information Disclosure: Skip CI loop prevention", () => {
    const content = fs.readFileSync(workflowPath, "utf8");
    assert.match(content, /\[skip ci\]/, "Auto-commit message must include [skip ci] to prevent recursive execution loops");
  });

  test("STRIDE Tampering: Cache buster parameter sanitization", () => {
    // Attempt malicious injection payload inside cache buster
    const maliciousPayload = `24" onload="alert(1)`;
    assert.throws(() => {
      updateReadmeCacheBuster(maliciousPayload, false);
    }, /Invalid cache buster format/, "Must reject non-alphanumeric cache buster strings");
  });
});
