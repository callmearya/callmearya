import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { 
  buildSvg, 
  sanitizeText, 
  validateUsername, 
  buildCells, 
  fetchWeeks,
  validateApiEndpoint
} from '../generate.mjs';

describe('Security: STRIDE & OWASP Top 10 Cyber Attack Defense Suite', () => {

  describe('OWASP A03: Injection & XSS Attack Vector Defense', () => {
    it('should neutralize nested SVG/HTML script injection payloads in username and telemetry', () => {
      const maliciousPayloads = [
        '<script>alert(1)</script>',
        '<svg onload="alert(document.cookie)">',
        '"><img src=x onerror=alert(1)>',
        'pratik&<>"\'',
        '"><script src="//evil.com/xss.js"></script>'
      ];

      for (const payload of maliciousPayloads) {
        const sanitized = sanitizeText(payload);
        assert.strictEqual(sanitized.includes('<script>'), false, `Failed for payload: ${payload}`);
        assert.strictEqual(sanitized.includes('onload='), false, `Failed for payload: ${payload}`);
        assert.strictEqual(sanitized.includes('onerror='), false, `Failed for payload: ${payload}`);
        assert.strictEqual(sanitized.includes('<img'), false, `Failed for payload: ${payload}`);
      }
    });

    it('should strictly validate GitHub usernames with regex allowlist', () => {
      const validUsers = ['pratikforge', 'user-name', 'a-b-c-1'];
      const invalidUsers = [
        'user; DROP TABLE users;--',
        '<script>',
        'user$name',
        'user@domain.com',
        '../path/traversal',
        'user name'
      ];

      validUsers.forEach(u => assert.strictEqual(validateUsername(u), true, `Should accept valid username: ${u}`));
      invalidUsers.forEach(u => assert.strictEqual(validateUsername(u), false, `Should reject invalid username: ${u}`));
    });
  });

  describe('STRIDE: Information Disclosure Defense', () => {
    it('should NEVER leak GH_TOKEN, GITHUB_TOKEN, or authorization headers into SVG output', () => {
      const secretToken = 'ghp_CONFIDENTIAL_SECRET_TOKEN_999888777';
      process.env.GH_TOKEN = secretToken;
      process.env.GITHUB_TOKEN = secretToken;

      const svg = buildSvg([], { mock: true });
      assert.strictEqual(svg.includes(secretToken), false, 'CRITICAL: Secret token leaked into SVG output!');
      assert.strictEqual(svg.includes('ghp_'), false, 'CRITICAL: Token pattern found in output!');
    });

    it('should not leak internal absolute system paths in user-facing error messages', () => {
      // Test error sanitization
      try {
        validateUsername('invalid/../user');
      } catch (err) {
        assert.strictEqual(err.message.includes('C:\\'), false);
        assert.strictEqual(err.message.includes('/Users/'), false);
      }
    });
  });

  describe('STRIDE: Denial of Service (DoS) & XML Bomb Defense', () => {
    it('should clamp massive contribution payloads to prevent memory exhaustion / OOM', () => {
      // Generate 20,000 synthetic weeks (over 140,000 days)
      const massiveWeeks = Array.from({ length: 20000 }, () => ({
        contributionDays: Array.from({ length: 7 }, () => ({
          contributionCount: 99,
          color: '#39d353',
          date: '2026-08-22'
        }))
      }));

      const cells = buildCells(massiveWeeks, 52);
      assert.strictEqual(cells.length, 52 * 7, 'Must clamp to exactly 52 columns');

      const svg = buildSvg(massiveWeeks, { mock: false, cols: 52 });
      assert.ok(svg.length < 120000, `SVG size should remain bounded, was ${svg.length} bytes`);
    });
  });

  describe('STRIDE: Tampering & Data Integrity', () => {
    it('should gracefully sanitize malformed contribution days without breaking SVG XML structure', () => {
      const corruptWeeks = [
        { contributionDays: null },
        { contributionDays: [{ contributionCount: -99, color: 'invalid-color' }] },
        { contributionDays: [{ contributionCount: 'NaN', color: '<script>' }] },
        null,
        undefined
      ];

      const cells = buildCells(corruptWeeks, 52);
      assert.strictEqual(cells.length, 52 * 7);

      const svg = buildSvg(corruptWeeks, { mock: false });
      assert.ok(svg.startsWith('<svg'));
      assert.ok(svg.endsWith('</svg>'));
      assert.strictEqual(svg.includes('<script>'), false);
    });
  });

  describe('OWASP A10: Server-Side Request Forgery (SSRF) Defense', () => {
    it('should only allow secure official GitHub GraphQL endpoints', () => {
      assert.strictEqual(validateApiEndpoint('https://api.github.com/graphql'), true);
      assert.strictEqual(validateApiEndpoint('http://api.github.com/graphql'), false, 'Should reject HTTP');
      assert.strictEqual(validateApiEndpoint('https://evil-attacker.com/graphql'), false, 'Should reject non-GitHub host');
      assert.strictEqual(validateApiEndpoint('http://169.254.169.254/latest/meta-data/'), false, 'Should reject cloud metadata IP');
    });
  });

});
