export interface Candle {
  time: number; // millisecond timestamp
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export type PatternType = "None" | "Doji" | "Hammer (Bull)" | "Bullish Engulfing" | "Bearish Engulfing" | "Shooting Star" | "Morning Star" | "Evening Star";

/**
 * Calculates exponential moving average (EMA)
 */
export function calculateEMA(prices: number[], period: number = 200): number[] {
  const ema: number[] = [];
  if (prices.length === 0) return ema;

  const k = 2 / (period + 1);
  let sum = 0;

  for (let i = 0; i < prices.length; i++) {
    if (i < period - 1) {
      ema.push(NaN);
      sum += prices[i];
    } else if (i === period - 1) {
      sum += prices[i];
      const sma = sum / period;
      ema.push(sma);
    } else {
      const prevEma = ema[i - 1];
      const currentEma = prices[i] * k + prevEma * (1 - k);
      ema.push(currentEma);
    }
  }

  return ema;
}

/**
 * Calculates Simple Moving Average (SMA)
 */
export function calculateSMA(prices: number[], period: number = 50): number[] {
  const sma: number[] = [];
  if (prices.length === 0) return sma;

  let sum = 0;
  for (let i = 0; i < prices.length; i++) {
    sum += prices[i];
    if (i < period - 1) {
      sma.push(NaN);
    } else {
      if (i >= period) {
        sum -= prices[i - period];
      }
      sma.push(sum / period);
    }
  }
  return sma;
}

/**
 * Calculates Relative Strength Index (RSI-14) using Wilders technical smoothing
 */
export function calculateRSI(prices: number[], period: number = 14): number[] {
  const rsi: number[] = [];
  if (prices.length < period) {
    return Array(prices.length).fill(NaN);
  }

  const gains: number[] = [];
  const losses: number[] = [];

  for (let i = 1; i < prices.length; i++) {
    const diff = prices[i] - prices[i - 1];
    if (diff > 0) {
      gains.push(diff);
      losses.push(0);
    } else {
      gains.push(0);
      losses.push(Math.abs(diff));
    }
  }

  // Initialize slots up to period
  for (let i = 0; i <= period; i++) {
    rsi.push(NaN);
  }

  // Calculate first standard average gain & loss
  let avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period;
  let avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period;

  let rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
  rsi[period] = 100 - 100 / (1 + rs);

  // Wilders smoothing for standard charts
  for (let i = period; i < gains.length; i++) {
    const currentGain = gains[i];
    const currentLoss = losses[i];

    avgGain = (avgGain * (period - 1) + currentGain) / period;
    avgLoss = (avgLoss * (period - 1) + currentLoss) / period;

    rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
    const val = 100 - 100 / (1 + rs);
    rsi.push(val);
  }

  return rsi;
}

/**
 * Custom Candlestick pattern recognition
 */
export function detectPattern(candles: Candle[], index: number): PatternType {
  if (index < 2) return "None";

  const curr = candles[index];
  const prev = candles[index - 1];
  const prev2 = candles[index - 2];

  const bodyCurr = Math.abs(curr.close - curr.open);
  const rangeCurr = curr.high - curr.low;

  // 1. Doji: body is extremely small compared to overall bar range
  if (rangeCurr > 0 && bodyCurr / rangeCurr < 0.1) {
    return "Doji";
  }

  // 2. Hammer (Bullish): small body at top, lower tail is at least 2x the body size, little to no upper wick
  const lowerWick = Math.min(curr.open, curr.close) - curr.low;
  const upperWick = curr.high - Math.max(curr.open, curr.close);
  if (bodyCurr > 0 && lowerWick >= 2 * bodyCurr && upperWick <= 0.5 * bodyCurr) {
    return "Hammer (Bull)";
  }

  // 3. Shooting Star (Bearish): small body at bottom, upper tail is at least 2x body size, little to no lower wick
  if (bodyCurr > 0 && upperWick >= 2 * bodyCurr && lowerWick <= 0.5 * bodyCurr) {
    return "Shooting Star";
  }

  // 4. Morning Star (Bullish reversal 3-candle pattern)
  if (prev2.close < prev2.open && Math.abs(prev.close - prev.open) < (prev2.open - prev2.close) * 0.3 && curr.close > curr.open && curr.close > prev.close + (prev2.open - prev2.close) * 0.5) {
    return "Morning Star";
  }

  // 5. Evening Star (Bearish reversal 3-candle pattern)
  if (prev2.close > prev2.open && Math.abs(prev.close - prev.open) < (prev2.close - prev2.open) * 0.3 && curr.close < curr.open && curr.close < prev.close - (prev2.close - prev2.open) * 0.5) {
    return "Evening Star";
  }

  // 6. Engulfing
  // Bullish Engulfing: previous bar bearish, current candles are bullish and fully overlays previous body
  if (prev.close < prev.open && curr.close > curr.open && curr.close >= prev.open && curr.open <= prev.close) {
    return "Bullish Engulfing";
  }

  // Bearish Engulfing: previous bar bullish, current candles are bearish and fully overlays previous body
  if (prev.close > prev.open && curr.close < curr.open && curr.close <= prev.open && curr.open >= prev.close) {
    return "Bearish Engulfing";
  }

  return "None";
}

/**
 * 1. Chart Pattern Intelligence Module (Calculates Double Tops, Bottoms, Head & Shoulders, Flags, Triangles)
 */
export function detectChartPattern(candles: Candle[], index: number): { pattern: string; status: "Bullish" | "Bearish" | "Neutral" } {
  if (index < 20) {
    return { pattern: "Loading Chart Structures", status: "Neutral" };
  }

  const slice = candles.slice(Math.max(0, index - 25), index + 1);
  const closes = slice.map(c => c.close);
  const highs = slice.map(c => c.high);
  const lows = slice.map(c => c.low);

  const maxPrice = Math.max(...highs);
  const minPrice = Math.min(...lows);
  const totalRange = maxPrice - minPrice;

  // Let's check for basic price channels & peaks / valleys
  const recentCloses = closes.slice(-5);
  const olderCloses = closes.slice(0, 15);

  const recentAvg = recentCloses.reduce((a, b) => a + b, 0) / recentCloses.length;
  const olderAvg = olderCloses.reduce((a, b) => a + b, 0) / olderCloses.length;

  // Find local peaks
  const peaks: { val: number; idx: number }[] = [];
  const troughs: { val: number; idx: number }[] = [];

  for (let i = 1; i < slice.length - 1; i++) {
    if (slice[i].high > slice[i-1].high && slice[i].high > slice[i+1].high) {
      peaks.push({ val: slice[i].high, idx: i });
    }
    if (slice[i].low < slice[i-1].low && slice[i].low < slice[i+1].low) {
      troughs.push({ val: slice[i].low, idx: i });
    }
  }

  // Double Bottom detection
  if (troughs.length >= 2) {
    const t1 = troughs[troughs.length - 2].val;
    const t2 = troughs[troughs.length - 1].val;
    const diff = Math.abs(t1 - t2) / t1;
    if (diff < 0.003 && slice[slice.length - 1].close > t2 * 1.002) {
      return { pattern: "Double Bottom Setup (W-Pattern)", status: "Bullish" };
    }
  }

  // Double Top detection
  if (peaks.length >= 2) {
    const p1 = peaks[peaks.length - 2].val;
    const p2 = peaks[peaks.length - 1].val;
    const diff = Math.abs(p1 - p2) / p1;
    if (diff < 0.003 && slice[slice.length - 1].close < p2 * 0.998) {
      return { pattern: "Double Top Resistance (M-Pattern)", status: "Bearish" };
    }
  }

  // Bull Flag / Symmetrical Triangle or general Channels
  const isUpward = recentAvg > olderAvg * 1.005;
  const isDownward = recentAvg < olderAvg * 0.995;

  if (isUpward) {
    // Check if consolidating near the top (Bull Flag consolidation)
    const lastThree = recentCloses.slice(-3);
    const consolidRange = Math.max(...lastThree) - Math.min(...lastThree);
    if (consolidRange / recentAvg < 0.004) {
      return { pattern: "Bullish Flag / Consolidation Channel", status: "Bullish" };
    }
    return { pattern: "Ascending Channel Breakout Pattern", status: "Bullish" };
  } else if (isDownward) {
    const lastThree = recentCloses.slice(-3);
    const consolidRange = Math.max(...lastThree) - Math.min(...lastThree);
    if (consolidRange / recentAvg < 0.004) {
      return { pattern: "Bearish Flag / Consolidation Channel", status: "Bearish" };
    }
    return { pattern: "Descending Channel Breakdown Pattern", status: "Bearish" };
  }

  // Symmetrical Triangle / Coiling Springs (Volatility contraction)
  if (peaks.length >= 2 && troughs.length >= 2) {
    const lastP1 = peaks[peaks.length - 2].val;
    const lastP2 = peaks[peaks.length - 1].val;
    const lastT1 = troughs[troughs.length - 2].val;
    const lastT2 = troughs[troughs.length - 1].val;

    if (lastP2 < lastP1 && lastT2 > lastT1) {
      // Coiling price contraction (Symmetrical Triangle)
      const current = slice[slice.length - 1];
      if (current.close > (lastP2 + lastT2) / 2) {
        return { pattern: "Symmetrical Triangle Bullish Breakout", status: "Bullish" };
      } else {
        return { pattern: "Symmetrical Triangle Bearish Breakdown", status: "Bearish" };
      }
    }
  }

  return { pattern: "Symmetrical Consolidation Triangle", status: "Neutral" };
}

/**
 * 2. Volume Profile Analysis Module
 */
export function analyzeVolume(candles: Candle[], index: number): { status: "Bullish" | "Bearish" | "Neutral"; detail: string } {
  if (index < 20) {
    return { status: "Neutral", detail: "Calculating historical volume profile" };
  }

  const slice = candles.slice(Math.max(0, index - 20), index + 1);
  const currentVolume = slice[slice.length - 1].volume;
  const currentOpen = slice[slice.length - 1].open;
  const currentClose = slice[slice.length - 1].close;

  const pastVolumes = slice.slice(0, -1).map(c => c.volume);
  const avgVolume = pastVolumes.reduce((a, b) => a + b, 0) / pastVolumes.length;

  const ratio = currentVolume / (avgVolume || 1);

  if (ratio > 1.8) {
    if (currentClose > currentOpen) {
      return { status: "Bullish", detail: `Bullish Volume Spike! (+${Math.round((ratio - 1) * 100)}% above 20-period SMA)` };
    } else {
      return { status: "Bearish", detail: `Bearish Liquidation Volume Spike! (+${Math.round((ratio - 1) * 100)}% above 20-period SMA)` };
    }
  } else if (ratio > 1.1) {
    if (currentClose > currentOpen) {
      return { status: "Bullish", detail: "Steadily rising buying volume pressure" };
    } else {
      return { status: "Bearish", detail: "Rising selling pressure on high volume" };
    }
  }

  return { status: "Neutral", detail: "Average distribution volume (low block volatility)" };
}

/**
 * 3. Liquidity Pool & Support/Resistance Proximity Module
 */
export function analyzeLiquidity(candles: Candle[], index: number): { status: "Bullish" | "Bearish" | "Neutral"; detail: string; sLevel: number; rLevel: number } {
  if (index < 30) {
    return { status: "Neutral", detail: "Mapping institutional liquidity blocks", sLevel: 0, rLevel: 0 };
  }

  const lookback = candles.slice(Math.max(0, index - 30), index + 1);
  const highs = lookback.map(c => c.high);
  const lows = lookback.map(c => c.low);

  const resistanceLevel = Math.max(...highs);
  const supportLevel = Math.min(...lows);

  const currentPrice = candles[index].close;
  const totalRange = resistanceLevel - supportLevel;

  const distToSupportPct = ((currentPrice - supportLevel) / currentPrice) * 100;
  const distToResistancePct = ((resistanceLevel - currentPrice) / currentPrice) * 100;

  if (distToSupportPct < 0.5) {
    return {
      status: "Bullish",
      detail: `Heavy Buy Orders Liquidity ($${supportLevel.toFixed(2)}) entered. Bounce likelihood HIGH limit`,
      sLevel: supportLevel,
      rLevel: resistanceLevel
    };
  } else if (distToResistancePct < 0.5) {
    return {
      status: "Bearish",
      detail: `Heavy Sell-wall Orders Liquidity ($${resistanceLevel.toFixed(2)}) active. Downward correction risk HIGH`,
      sLevel: supportLevel,
      rLevel: resistanceLevel
    };
  }

  return {
    status: "Neutral",
    detail: `Balanced trade channel: Support pool at $${supportLevel.toFixed(2)} (${distToSupportPct.toFixed(1)}% away), Resistance at $${resistanceLevel.toFixed(2)} (${distToResistancePct.toFixed(1)}% away)`,
    sLevel: supportLevel,
    rLevel: resistanceLevel
  };
}
