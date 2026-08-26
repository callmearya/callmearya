import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { 
  sanitizeText, 
  buildCells, 
  buildSvg, 
  generateMockWeeks,
  computeStats,
  computeArcadeScore,
  buildShieldBar,
  selectTargets,
  columnToTimeFraction,
  buildMonotonicKeyTimes,
  buildTargetLockBrackets,
  buildProminentRailguns,
  buildExplosiveImpacts,
  buildDynamicReticle,
  buildGrid,
  buildMonthLabels,
  JET_X_START,
  JET_X_END,
  THEME
} from '../generate.mjs';

describe('TDD: Precision Closed-Form Spline Kinematics & Synchronized Combat', () => {
  describe('Input Sanitization & Data Parsing', () => {
    it('should sanitize XML/HTML special characters and disarm inline event handlers', () => {
      const malicious = '<script>alert("xss")</script>&"\' onload="evil()"';
      const clean = sanitizeText(malicious);
      assert.strictEqual(clean.includes('<script>'), false);
      assert.strictEqual(clean.includes('onload='), false);
      assert.strictEqual(clean.includes('&lt;script&gt;'), true);
    });

    it('should correctly calculate arcade score from contribution count', () => {
      assert.strictEqual(computeArcadeScore(766), '766,000 PTS');
      assert.strictEqual(computeArcadeScore(837), '837,000 PTS');
      assert.strictEqual(computeArcadeScore(0), '0 PTS');
      assert.strictEqual(computeArcadeScore(1250), '1,250,000 PTS');
    });

    it('should accurately compute total contributions from both weeks and cells array structures', () => {
      const mockWeeks = generateMockWeeks(52);
      const statsFromWeeks = computeStats(mockWeeks);
      assert.ok(statsFromWeeks.total > 0);
      assert.ok(statsFromWeeks.activeDays > 0);

      const cells = buildCells(mockWeeks, 52);
      const statsFromCells = computeStats(cells);
      assert.strictEqual(statsFromCells.total, statsFromWeeks.total);
      assert.strictEqual(statsFromCells.activeDays, statsFromWeeks.activeDays);
    });

    it('should generate 10 segmented glowing shield health blocks', () => {
      const shieldSvg = buildShieldBar(100);
      assert.ok(shieldSvg.includes('<rect'));
      const blockCount = (shieldSvg.match(/<rect /g) || []).length;
      assert.strictEqual(blockCount, 10);
    });
  });

  describe('Closed-Form Spline Kinematics & Mathematical Precision', () => {
    it('should calculate exact time fractions for boundary and center columns without singularity', () => {
      const col0 = columnToTimeFraction(0, 51);
      assert.strictEqual(Number(col0.t_fwd.toFixed(4)), 0.0000);
      assert.strictEqual(Number(col0.t_ret.toFixed(4)), 1.0000);

      const col51 = columnToTimeFraction(51, 51);
      assert.strictEqual(Number(col51.t_fwd.toFixed(4)), 0.5000);
      assert.strictEqual(Number(col51.t_ret.toFixed(4)), 0.5000);

      const colMid = columnToTimeFraction(25.5, 51);
      assert.strictEqual(Number(colMid.t_fwd.toFixed(4)), 0.2500);
      assert.strictEqual(Number(colMid.t_ret.toFixed(4)), 0.7500);
    });

    it('should mathematically guarantee jet position aligns with target column within 0.5px at t_hit', () => {
      const mockWeeks = generateMockWeeks(52);
      const cells = buildCells(mockWeeks, 52);
      const targets = selectTargets(cells);

      for (const t of targets) {
        // Forward sweep evaluation (0..0.5)
        const pExpected = t.col / 51;
        const expectedX = JET_X_START + pExpected * (JET_X_END - JET_X_START);
        assert.ok(
          Math.abs(expectedX - t.cx) <= 0.5,
          `Forward alignment error at col ${t.col}: expected ${expectedX}, got ${t.cx}`
        );

        // Verify t_hit_fwd is within valid bounds [0.001, 0.499]
        assert.ok(t.k_hit_fwd >= 0 && t.k_hit_fwd <= 0.5);
        assert.ok(t.k_hit_ret >= 0.5 && t.k_hit_ret <= 1.0);
      }
    });
  });

  describe('Strict Monotonic SMIL Timeline Builder', () => {
    it('should generate strictly ascending keyTimes and prevent duplicate float collapse', () => {
      const rawEvents = [
        { time: 0.12345, value: '0' },
        { time: 0.12346, value: '1' }, // extremely close
        { time: 0.45000, value: '0' },
        { time: 0.45000, value: '1' }  // identical duplicate
      ];
      const result = buildMonotonicKeyTimes(rawEvents);
      const times = result.keyTimes.split('; ').map(Number);
      
      for (let i = 1; i < times.length; i++) {
        assert.ok(times[i] > times[i - 1], `Non-monotonic keyTimes detected: ${times[i - 1]} >= ${times[i]}`);
      }
      assert.strictEqual(times[0], 0);
      assert.strictEqual(times[times.length - 1], 1);
    });
  });

  describe('Target Selection & Decoupled Combat Layer', () => {
    it('should NEVER target empty (count === 0 / level 0) cells in asymmetric heatmaps', () => {
      // Simulate user profile: 0 contributions in cols 0..29, large contributions in cols 30..51
      const asymmetricWeeks = Array.from({ length: 52 }, (_, col) => ({
        contributionDays: Array.from({ length: 7 }, (_, row) => {
          if (col >= 30) {
            return { contributionCount: (col % 5) + 3, color: THEME.palette[3], date: '2026-06-01' };
          }
          return { contributionCount: 0, color: THEME.palette[0], date: '2026-01-01' };
        })
      }));
      const cells = buildCells(asymmetricWeeks, 52);
      const targets = selectTargets(cells);

      assert.ok(targets.length > 0, 'Should find targets in active columns');
      for (const t of targets) {
        assert.ok(t.col >= 30, `Target was chosen in empty column ${t.col} (< 30)`);
        assert.ok(t.count > 0, `Target in col ${t.col} has 0 count`);
        assert.notStrictEqual(t.color, THEME.palette[0], `Target in col ${t.col} has level-0 empty color`);
      }
    });

    it('should prioritize highest contribution count nodes and maintain minimum 3-column spacing', () => {
      const mockWeeks = generateMockWeeks(52);
      const cells = buildCells(mockWeeks, 52);
      const targets = selectTargets(cells);

      assert.ok(targets.length >= 1 && targets.length <= 8, `Target count ${targets.length} out of bounds`);
      
      // Verify all chosen targets have count > 0 and no spacing violation (< 3)
      for (let i = 0; i < targets.length; i++) {
        assert.ok(targets[i].count > 0, `Target ${i} has non-positive count: ${targets[i].count}`);
        assert.notStrictEqual(targets[i].color, THEME.palette[0]);
        if (i > 0) {
          const diff = targets[i].col - targets[i - 1].col;
          assert.ok(diff >= 3, `Target spacing violation between col ${targets[i - 1].col} and ${targets[i].col} (diff: ${diff})`);
        }
      }
    });

    it('should return 0 targets for completely empty heatmaps (0 contributions) gracefully without error', () => {
      const emptyWeeks = Array.from({ length: 52 }, () => ({
        contributionDays: Array.from({ length: 7 }, () => ({ contributionCount: 0, color: THEME.palette[0], date: '2026-01-01' }))
      }));
      const cells = buildCells(emptyWeeks, 52);
      const targets = selectTargets(cells);
      assert.ok(Array.isArray(targets));
      assert.strictEqual(targets.length, 0, `Expected 0 targets for empty heatmap, got ${targets.length}`);

      // Consumer builders must handle empty targets safely
      const lockSvg = buildTargetLockBrackets(targets);
      const railgunSvg = buildProminentRailguns(targets);
      const impactSvg = buildExplosiveImpacts(targets);
      const gridSvg = buildGrid(cells, targets);

      assert.ok(lockSvg.includes('id="target-lock-brackets"'));
      assert.ok(railgunSvg.includes('id="world-space-railguns"'));
      assert.ok(impactSvg.includes('id="explosive-impacts"'));
      assert.ok(gridSvg.includes('<rect'));
    });

    it('should generate transient holographic lock brackets for each target', () => {
      const mockWeeks = generateMockWeeks(52);
      const cells = buildCells(mockWeeks, 52);
      const targets = selectTargets(cells);
      const lockSvg = buildTargetLockBrackets(targets);
      
      assert.ok(lockSvg.includes('id="target-lock-brackets"'));
      assert.ok(lockSvg.includes('class="lock-bracket"'));
    });

    it('should generate world-space vertical railgun lances fired on arrival', () => {
      const mockWeeks = generateMockWeeks(52);
      const cells = buildCells(mockWeeks, 52);
      const targets = selectTargets(cells);
      const railgunSvg = buildProminentRailguns(targets);
      
      assert.ok(railgunSvg.includes('id="world-space-railguns"'));
      assert.ok(railgunSvg.includes('class="railgun-lance"'));
      assert.ok(railgunSvg.includes('dur="18s"'));
    });

    it('should generate crisp 14px maximum shockwave detonations without visual grid occlusion', () => {
      const mockWeeks = generateMockWeeks(52);
      const cells = buildCells(mockWeeks, 52);
      const targets = selectTargets(cells);
      const impactSvg = buildExplosiveImpacts(targets);
      
      assert.ok(impactSvg.includes('class="explosive-impact"'));
      assert.ok(impactSvg.includes('class="shockwave-primary"'));
      // Verify radius values for attributeName="r" do not exceed 14
      const rAnimateMatches = impactSvg.match(/<animate attributeName="r"[^>]+values="([^"]+)"/g) || [];
      assert.ok(rAnimateMatches.length > 0);
      for (const m of rAnimateMatches) {
        const valStr = m.match(/values="([^"]+)"/)[1];
        const radii = valStr.split(';').map(s => Number(s.trim()));
        for (const r of radii) {
          assert.ok(r <= 14, `Shockwave radius ${r} exceeds 14px`);
        }
      }
    });
  });

  describe('Arcade HUD Layout & Visual Structure', () => {
    it('should produce 1180x340 Arcade Space Defender canvas matching dark.svg aesthetics', () => {
      const svg = buildSvg([], { mock: true });
      assert.ok(svg.startsWith('<svg'));
      assert.ok(svg.endsWith('</svg>'));
      assert.ok(svg.includes('viewBox="0 0 1180 340"'));
      assert.ok(svg.includes('SIGNAL:'));
      assert.ok(svg.includes('TECH ENTHUSIAST'));
      assert.ok(svg.includes('MODE:'));
      assert.ok(svg.includes('CURIOUS · BUILDING'));
      assert.ok(svg.includes('SHIELDS: 100%'));
      assert.ok(svg.includes('id="boresight-reticle"'));
      assert.ok(svg.includes('id="target-lock-brackets"'));
      assert.ok(svg.includes('id="world-space-railguns"'));
    });

    it('should generate rolling month labels matching 52-week chronological window', () => {
      const mockWeeks = generateMockWeeks(52);
      const cells = buildCells(mockWeeks, 52);
      const monthSvg = buildMonthLabels(cells);
      assert.ok(monthSvg.includes('class="axis-label"'));
      const textMatches = monthSvg.match(/<text [^>]+>([^<]+)<\/text>/g) || [];
      assert.ok(textMatches.length >= 10 && textMatches.length <= 13);
    });
  });

  describe('Profile Terminal Monospace Alignment & Boundary Invariance', () => {
    it('should ensure all terminal bio rows in dark.svg and light.svg align values at exact 28-character column offset', async () => {
      const fs = await import('node:fs');
      for (const file of ['dark.svg', 'light.svg']) {
        const content = fs.readFileSync(file, 'utf8');
        // Extract clip-path lines lc1..lc18 that contain <tspan class="value">
        const lineMatches = content.match(/<g clip-path="url\(#lc(?:[1-9]|1[0-8])\)">.*?<\/g>/g) || [];
        for (const g of lineMatches) {
          if (!g.includes('class="value"')) continue;
          // Extract text inside tspans before class="value"
          const prefixMatch = g.match(/<text [^>]+>(.*?)<tspan [^>]*class="value"/);
          if (prefixMatch) {
            // Strip XML tags to get raw character count
            const rawPrefix = prefixMatch[1].replace(/<[^>]+>/g, '');
            assert.strictEqual(
              rawPrefix.length,
              28,
              `File ${file} line has prefix length ${rawPrefix.length} instead of 28: "${rawPrefix}"`
            );
          }
        }
      }
    });
  });
});
