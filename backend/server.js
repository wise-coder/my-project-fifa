const path = require("path");
const fs = require("fs");
const crypto = require("crypto");

const express = require("express");
const cors = require("cors");
const multer = require("multer");
const bcrypt = require("bcryptjs");
const jwt = require("jsonwebtoken");
const cookieParser = require("cookie-parser");
const Database = require("better-sqlite3");
const ENV_PATH = path.join(__dirname, ".env");
require("dotenv").config({ path: ENV_PATH });

const app = express();

const PORT = Number(process.env.PORT || 5000);
const SECRET_KEY = process.env.SECRET_KEY || "fifa-stats-secret-key-2024";
const MAX_CONTENT_LENGTH = Number(process.env.MAX_CONTENT_LENGTH || 5 * 1024 * 1024);
const ALLOW_FALLBACK_SCORING = String(process.env.ALLOW_FALLBACK_SCORING || "false").toLowerCase() === "true";
const ADMIN_BOOTSTRAP_EMAIL = (process.env.ADMIN_EMAIL || "serge.wiseabijuru5@gmail.com").toLowerCase();
const ADMIN_BOOTSTRAP_PASSWORD = process.env.ADMIN_PASSWORD || "2008@abanaBEZA";
const UPLOAD_DIR = path.join(__dirname, "uploads");
const DB_PATH = path.join(__dirname, "fifa_stats.db");

const ALLOWED_ORIGINS = [
  "http://127.0.0.1:5501",
  "http://localhost:5501",
  "http://127.0.0.1:5000",
  "http://localhost:5000",
];

if (!fs.existsSync(UPLOAD_DIR)) {
  fs.mkdirSync(UPLOAD_DIR, { recursive: true });
}

const db = new Database(DB_PATH);
db.pragma("journal_mode = WAL");

// Keep schema close to the previous Flask models so existing frontend payloads stay unchanged.
function initDatabase() {
  db.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      email TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      total_score INTEGER DEFAULT 0,
      matches_played INTEGER DEFAULT 0,
      is_active INTEGER DEFAULT 1,
      is_admin INTEGER DEFAULT 0,
      is_banned INTEGER DEFAULT 0,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS competitions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      description TEXT,
      start_date DATETIME,
      end_date DATETIME,
      status TEXT DEFAULT 'upcoming',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS matches (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      image_filename TEXT,
      image_hash TEXT,
      match_score INTEGER DEFAULT 0,
      goals INTEGER DEFAULT 0,
      assists INTEGER DEFAULT 0,
      possession INTEGER DEFAULT 0,
      shots INTEGER DEFAULT 0,
      shots_on_target INTEGER DEFAULT 0,
      pass_accuracy INTEGER DEFAULT 0,
      tackles INTEGER DEFAULT 0,
      competition_id INTEGER,
      is_verified INTEGER DEFAULT 0,
      rejection_reason TEXT,
      date_uploaded DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id),
      FOREIGN KEY (competition_id) REFERENCES competitions(id)
    );

    CREATE TABLE IF NOT EXISTS notifications (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      title TEXT,
      message TEXT NOT NULL,
      type TEXT DEFAULT 'info',
      is_read INTEGER DEFAULT 0,
      date_created DATETIME DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE INDEX IF NOT EXISTS idx_matches_user_id ON matches(user_id);
    CREATE INDEX IF NOT EXISTS idx_matches_image_hash ON matches(image_hash);
    CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
  `);
}

initDatabase();

app.use(express.json({ limit: "2mb" }));
app.use(cookieParser());
// CORS is configured for Live Server and credentialed requests.
app.use(
  cors({
    origin(origin, callback) {
      if (!origin || ALLOWED_ORIGINS.includes(origin)) {
        callback(null, true);
        return;
      }
      callback(new Error("Origin not allowed by CORS"));
    },
    credentials: true,
    methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Authorization", "X-Requested-With"],
    exposedHeaders: ["Content-Length", "Content-Type"],
    maxAge: 3600,
  }),
);

app.use("/api/uploads", express.static(UPLOAD_DIR));

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, UPLOAD_DIR),
  filename: (_req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    cb(null, `${crypto.randomUUID().replace(/-/g, "")}_${Date.now()}${ext}`);
  },
});

// Multer stores uploaded screenshots locally in backend/uploads.
const upload = multer({
  storage,
  limits: { fileSize: MAX_CONTENT_LENGTH },
  fileFilter: (_req, file, cb) => {
    const allowed = [".png", ".jpg", ".jpeg"];
    const ext = path.extname(file.originalname).toLowerCase();
    if (!allowed.includes(ext)) {
      cb(new Error("Invalid file type. Allowed: PNG, JPG, JPEG"));
      return;
    }
    cb(null, true);
  },
});

function jsonResponse(res, { success = true, message = "", data = undefined, statusCode = 200 }) {
  const payload = { success, message };
  if (data !== undefined) payload.data = data;
  return res.status(statusCode).json(payload);
}

function normalizeBool(value) {
  return value === 1 || value === true;
}

function userToDict(row, includePrivate = false) {
  return {
    id: row.id,
    username: row.username,
    ...(includePrivate ? { email: row.email } : {}),
    total_score: row.total_score || 0,
    matches_played: row.matches_played || 0,
    is_active: normalizeBool(row.is_active),
    is_admin: normalizeBool(row.is_admin),
    is_banned: normalizeBool(row.is_banned),
    created_at: row.created_at ? new Date(row.created_at).toISOString() : null,
  };
}

function matchToDict(row) {
  return {
    id: row.id,
    user_id: row.user_id,
    image_filename: row.image_filename,
    match_score: row.match_score,
    goals: row.goals,
    assists: row.assists,
    possession: row.possession,
    shots: row.shots,
    shots_on_target: row.shots_on_target,
    pass_accuracy: row.pass_accuracy,
    tackles: row.tackles,
    competition_id: row.competition_id,
    is_verified: normalizeBool(row.is_verified),
    rejection_reason: row.rejection_reason,
    date_uploaded: row.date_uploaded ? new Date(row.date_uploaded).toISOString() : null,
  };
}

function notificationToDict(row) {
  return {
    id: row.id,
    user_id: row.user_id,
    title: row.title,
    message: row.message,
    type: row.type,
    is_read: normalizeBool(row.is_read),
    date: row.date_created ? new Date(row.date_created).toISOString() : null,
  };
}

function createToken(userId) {
  return jwt.sign({ userId }, SECRET_KEY, { expiresIn: "7d" });
}

function getTokenFromRequest(req) {
  const authHeader = req.headers.authorization;
  if (authHeader && authHeader.startsWith("Bearer ")) {
    return authHeader.slice("Bearer ".length);
  }
  if (req.cookies.auth_token) {
    return req.cookies.auth_token;
  }
  return null;
}

function authRequired(req, res, next) {
  const token = getTokenFromRequest(req);
  if (!token) {
    return jsonResponse(res, { success: false, message: "Authentication required", statusCode: 401 });
  }

  try {
    const payload = jwt.verify(token, SECRET_KEY);
    const user = db.prepare("SELECT * FROM users WHERE id = ? LIMIT 1").get(payload.userId);

    if (!user || !normalizeBool(user.is_active) || normalizeBool(user.is_banned)) {
      return jsonResponse(res, { success: false, message: "Authentication required", statusCode: 401 });
    }

    req.user = user;
    next();
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Authentication required", statusCode: 401 });
  }
}

function adminRequired(req, res, next) {
  return authRequired(req, res, () => {
    if (!normalizeBool(req.user?.is_admin)) {
      return jsonResponse(res, { success: false, message: "Admin privileges required", statusCode: 403 });
    }
    return next();
  });
}

function calculateImageHash(filepath) {
  const hasher = crypto.createHash("sha256");
  const data = fs.readFileSync(filepath);
  hasher.update(data);
  return hasher.digest("hex");
}

// Rotates Gemini keys and temporarily skips keys with repeated failures.
class APIKeyManager {
  constructor() {
    this.keys = [];
    this.keyUsage = new Map();
    this.keyErrors = new Map();
    this.currentKeyIndex = 0;
    this.loadKeys();
  }

  loadKeys() {
    this.keys = [];
    this.keyUsage = new Map();
    this.keyErrors = new Map();
    this.currentKeyIndex = 0;

    const commaKeys = (process.env.GEMINI_API_KEYS || "")
      .split(",")
      .map((k) => k.trim())
      .filter(Boolean);
    const dedup = new Set(commaKeys);

    for (let i = 1; i <= 4; i += 1) {
      const key = process.env[`GEMINI_API_KEY_${i}`];
      if (key) dedup.add(key);
    }

    this.keys = Array.from(dedup);

    this.keys.forEach((k) => {
      this.keyUsage.set(k, 0);
      this.keyErrors.set(k, 0);
    });
  }

  getKey() {
    if (!this.keys.length) return null;

    for (let i = 0; i < this.keys.length; i += 1) {
      const key = this.keys[this.currentKeyIndex];
      const errors = this.keyErrors.get(key) || 0;
      if (errors < 5) return key;
      this.rotate();
    }

    this.keys.forEach((k) => this.keyErrors.set(k, 0));
    return this.keys[0];
  }

  rotate() {
    if (!this.keys.length) return;
    this.currentKeyIndex = (this.currentKeyIndex + 1) % this.keys.length;
  }

  recordUsage(key, success = true) {
    if (!key) return;
    this.keyUsage.set(key, (this.keyUsage.get(key) || 0) + 1);
    if (!success) {
      this.keyErrors.set(key, (this.keyErrors.get(key) || 0) + 1);
      this.rotate();
    }
  }

  addKey(key) {
    if (!key || this.keys.includes(key)) return false;
    this.keys.push(key);
    this.keyUsage.set(key, 0);
    this.keyErrors.set(key, 0);
    return true;
  }

  getUsageStats() {
    const totalRequests = this.keys.reduce((sum, key) => sum + (this.keyUsage.get(key) || 0), 0);
    const activeKeys = this.keys.filter((key) => (this.keyErrors.get(key) || 0) < 5).length;
    return {
      total_keys: this.keys.length,
      active_keys: activeKeys,
      total_requests: totalRequests,
      keys: this.keys.map((key) => ({
        prefix: key.length > 10 ? `${key.slice(0, 10)}...` : key,
        usage: this.keyUsage.get(key) || 0,
        errors: this.keyErrors.get(key) || 0,
        status: (this.keyErrors.get(key) || 0) < 5 ? "active" : "error",
      })),
    };
  }

  reloadFromEnv() {
    this.loadKeys();
  }
}

const apiKeyManager = new APIKeyManager();

function persistApiKeysToEnv() {
  const keysValue = apiKeyManager.keys.join(",");
  let content = "";

  if (fs.existsSync(ENV_PATH)) {
    content = fs.readFileSync(ENV_PATH, "utf8");
  }

  const line = `GEMINI_API_KEYS=${keysValue}`;
  if (/^GEMINI_API_KEYS=.*/m.test(content)) {
    content = content.replace(/^GEMINI_API_KEYS=.*/m, line);
  } else {
    content = content ? `${content.trimEnd()}\n${line}\n` : `${line}\n`;
  }

  fs.writeFileSync(ENV_PATH, content, "utf8");
  process.env.GEMINI_API_KEYS = keysValue;
}

function fallbackAnalysis() {
  if (!ALLOW_FALLBACK_SCORING) {
    return {
      success: false,
      is_valid_screenshot: false,
      error: "AI validation unavailable",
      analysis_notes: "Fallback scoring is disabled",
      is_fallback: true,
    };
  }

  // Optional dev-only mode (disabled by default).
  const randomInt = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min;
  const shots = randomInt(3, 15);
  return {
    success: true,
    is_valid_screenshot: true,
    goals: randomInt(0, 5),
    assists: randomInt(0, 2),
    possession: randomInt(35, 65),
    shots,
    shots_on_target: randomInt(1, Math.min(shots, 8)),
    pass_accuracy: randomInt(60, 95),
    tackles: randomInt(0, 8),
    analysis_notes: "Fallback mode enabled by ALLOW_FALLBACK_SCORING=true",
    is_fallback: true,
  };
}

function parseGeminiResponse(text) {
  try {
    const match = text.match(/\{[\s\S]*\}/);
    if (!match) return null;

    const parsed = JSON.parse(match[0]);
    return {
      success: true,
      is_valid_screenshot: parsed.is_valid_screenshot !== false,
      goals: Number(parsed.goals || 0),
      assists: Number(parsed.assists || 0),
      possession: Number(parsed.possession || 0),
      shots: Number(parsed.shots || 0),
      shots_on_target: Number(parsed.shots_on_target || 0),
      pass_accuracy: Number(parsed.pass_accuracy || 0),
      tackles: Number(parsed.tackles || 0),
      analysis_notes: String(parsed.analysis_notes || ""),
    };
  } catch (_e) {
    return null;
  }
}

function validateAIStats(result) {
  if (!result || result.is_valid_screenshot !== true) return false;

  const goals = Number(result.goals);
  const assists = Number(result.assists);
  const possession = Number(result.possession);
  const shots = Number(result.shots);
  const shotsOnTarget = Number(result.shots_on_target);
  const passAccuracy = Number(result.pass_accuracy);
  const tackles = Number(result.tackles);

  if ([goals, assists, possession, shots, shotsOnTarget, passAccuracy, tackles].some((v) => Number.isNaN(v))) {
    return false;
  }

  if (goals < 0 || goals > 20) return false;
  if (assists < 0 || assists > 20) return false;
  if (possession < 0 || possession > 100) return false;
  if (shots < 0 || shots > 60) return false;
  if (shotsOnTarget < 0 || shotsOnTarget > 40) return false;
  if (shotsOnTarget > shots) return false;
  if (passAccuracy < 0 || passAccuracy > 100) return false;
  if (tackles < 0 || tackles > 50) return false;

  return true;
}

// AI extractor with fallback mode, keeping the same output fields as the Flask service.
async function analyzeScreenshotWithGemini(imagePath) {
  const key = apiKeyManager.getKey();
  if (!key) return fallbackAnalysis();

  try {
    const imageBytes = fs.readFileSync(imagePath);
    const mime = path.extname(imagePath).toLowerCase() === ".png" ? "image/png" : "image/jpeg";

    const prompt = `You are a strict FIFA/football post-match statistics screenshot validator.
Only return is_valid_screenshot=true if this is clearly a real football match statistics/result screen.
If this is a person photo, selfie, random social image, non-football UI, or unclear image, return is_valid_screenshot=false.
Extract:
1. Goals
2. Assists
3. Possession percentage
4. Shots
5. Shots on Target
6. Pass Accuracy percentage
7. Tackles
8. is_valid_screenshot

Respond only with valid JSON:
{
  "is_valid_screenshot": true,
  "goals": 0,
  "assists": 0,
  "possession": 0,
  "shots": 0,
  "shots_on_target": 0,
  "pass_accuracy": 0,
  "tackles": 0,
  "analysis_notes": "brief explanation"
}`;

    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${encodeURIComponent(key)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [
            {
              role: "user",
              parts: [
                { text: prompt },
                {
                  inline_data: {
                    mime_type: mime,
                    data: imageBytes.toString("base64"),
                  },
                },
              ],
            },
          ],
        }),
      },
    );

    const payload = await response.json();
    if (!response.ok) {
      apiKeyManager.recordUsage(key, false);
      return fallbackAnalysis();
    }

    const text = payload?.candidates?.[0]?.content?.parts?.map((p) => p.text || "").join("\n") || "";
    const parsed = parseGeminiResponse(text);
    if (!parsed) {
      apiKeyManager.recordUsage(key, false);
      return fallbackAnalysis();
    }

    if (!validateAIStats(parsed)) {
      apiKeyManager.recordUsage(key, true);
      return {
        ...parsed,
        success: true,
        is_valid_screenshot: false,
        analysis_notes: "Image failed strict football-statistics validation",
      };
    }

    apiKeyManager.recordUsage(key, true);
    return parsed;
  } catch (_err) {
    apiKeyManager.recordUsage(key, false);
    return fallbackAnalysis();
  }
}

// Score calculation mirrors the previous Python scoring rules.
function calculateScoreFromAI(aiResult) {
  const config = {
    goals: 15,
    assists: 10,
    shots_on_target: 2,
    possession_bonus: 5,
    clean_sheet: 10,
    pass_accuracy_bonus: 3,
    tackles: 2,
    max_score: 100,
  };

  const breakdown = {};
  let totalPoints = 0;

  const goals = Number(aiResult.goals || 0);
  const assists = Number(aiResult.assists || 0);
  const shotsOnTarget = Number(aiResult.shots_on_target || 0);
  const tackles = Number(aiResult.tackles || 0);
  const possession = Number(aiResult.possession || 0);
  const passAccuracy = Number(aiResult.pass_accuracy || 0);

  breakdown.goals = goals * config.goals;
  totalPoints += breakdown.goals;
  breakdown.assists = assists * config.assists;
  totalPoints += breakdown.assists;
  breakdown.shots_on_target = shotsOnTarget * config.shots_on_target;
  totalPoints += breakdown.shots_on_target;
  breakdown.tackles = tackles * config.tackles;
  totalPoints += breakdown.tackles;

  if (possession > 50) {
    breakdown.possession_bonus = config.possession_bonus;
    totalPoints += config.possession_bonus;
  }
  if (passAccuracy > 80) {
    breakdown.pass_accuracy_bonus = config.pass_accuracy_bonus;
    totalPoints += config.pass_accuracy_bonus;
  }

  return {
    total_score: Math.min(totalPoints, config.max_score),
    score_breakdown: breakdown,
    raw_points: totalPoints,
    max_score: config.max_score,
  };
}

function createNotification(userId, message, title = null, type = "info") {
  db.prepare(
    "INSERT INTO notifications (user_id, title, message, type, is_read, date_created) VALUES (?, ?, ?, ?, 0, CURRENT_TIMESTAMP)",
  ).run(userId, title, message, type);
}

function getUniqueBootstrapAdminUsername(baseUsername = "admin_serge") {
  let username = baseUsername;
  let counter = 1;
  while (db.prepare("SELECT id FROM users WHERE username = ? LIMIT 1").get(username)) {
    counter += 1;
    username = `${baseUsername}_${counter}`;
  }
  return username;
}

function getOrCreateBootstrapAdmin() {
  let adminUser = db.prepare("SELECT * FROM users WHERE email = ? LIMIT 1").get(ADMIN_BOOTSTRAP_EMAIL);
  const passwordHash = bcrypt.hashSync(String(ADMIN_BOOTSTRAP_PASSWORD), 10);

  if (!adminUser) {
    const username = getUniqueBootstrapAdminUsername();
    const insert = db
      .prepare(
        "INSERT INTO users (username, email, password_hash, total_score, matches_played, is_active, is_admin, is_banned, created_at, updated_at) VALUES (?, ?, ?, 0, 0, 1, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
      )
      .run(username, ADMIN_BOOTSTRAP_EMAIL, passwordHash);

    adminUser = db.prepare("SELECT * FROM users WHERE id = ?").get(insert.lastInsertRowid);
    createNotification(adminUser.id, "Admin account is ready.", "Admin Access", "success");
    return adminUser;
  }

  db.prepare(
    "UPDATE users SET password_hash = ?, is_admin = 1, is_active = 1, is_banned = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
  ).run(passwordHash, adminUser.id);

  return db.prepare("SELECT * FROM users WHERE id = ?").get(adminUser.id);
}

app.get("/api/health", (_req, res) => jsonResponse(res, { message: "OK" }));

app.post("/api/register", (req, res) => {
  try {
    const { username, email, password } = req.body || {};
    if (!username || !email || !password) {
      return jsonResponse(res, { success: false, message: "username, email, and password are required", statusCode: 400 });
    }

    const cleanUsername = String(username).trim();
    const cleanEmail = String(email).trim().toLowerCase();
    if (cleanUsername.length < 3) {
      return jsonResponse(res, { success: false, message: "Username must be at least 3 characters", statusCode: 400 });
    }
    if (String(password).length < 6) {
      return jsonResponse(res, { success: false, message: "Password must be at least 6 characters", statusCode: 400 });
    }

    const existingByUsername = db.prepare("SELECT id FROM users WHERE username = ? LIMIT 1").get(cleanUsername);
    if (existingByUsername) {
      return jsonResponse(res, { success: false, message: "Username already exists", statusCode: 400 });
    }
    const existingByEmail = db.prepare("SELECT id FROM users WHERE email = ? LIMIT 1").get(cleanEmail);
    if (existingByEmail) {
      return jsonResponse(res, { success: false, message: "Email already exists", statusCode: 400 });
    }

    const passwordHash = bcrypt.hashSync(String(password), 10);
    const insert = db
      .prepare(
        "INSERT INTO users (username, email, password_hash, total_score, matches_played, is_active, is_admin, is_banned, created_at, updated_at) VALUES (?, ?, ?, 0, 0, 1, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
      )
      .run(cleanUsername, cleanEmail, passwordHash);
    const newUser = db.prepare("SELECT * FROM users WHERE id = ?").get(insert.lastInsertRowid);

    createNotification(
      newUser.id,
      "Welcome to FIFA Stats! Start uploading your match screenshots to track your progress.",
      "Welcome!",
      "info",
    );

    return jsonResponse(res, {
      success: true,
      message: "Registration successful!",
      statusCode: 201,
      data: { user: userToDict(newUser, true) },
    });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Registration failed", statusCode: 500 });
  }
});

app.post("/api/login", (req, res) => {
  try {
    const { email, password } = req.body || {};
    if (!email || !password) {
      return jsonResponse(res, { success: false, message: "Email and password are required", statusCode: 400 });
    }

    const cleanEmail = String(email).trim().toLowerCase();

    // Bootstrap admin login: no registration required for this fixed credential pair.
    if (cleanEmail === ADMIN_BOOTSTRAP_EMAIL && String(password) === ADMIN_BOOTSTRAP_PASSWORD) {
      const adminUser = getOrCreateBootstrapAdmin();
      const token = createToken(adminUser.id);

      res.cookie("auth_token", token, {
        httpOnly: true,
        secure: false,
        sameSite: "lax",
        maxAge: 7 * 24 * 60 * 60 * 1000,
      });

      return jsonResponse(res, {
        success: true,
        message: "Login successful",
        data: { token, user: userToDict(adminUser, true) },
      });
    }

    const user = db.prepare("SELECT * FROM users WHERE email = ? LIMIT 1").get(cleanEmail);
    if (!user) {
      return jsonResponse(res, { success: false, message: "Invalid credentials", statusCode: 401 });
    }
    if (!normalizeBool(user.is_active) || normalizeBool(user.is_banned)) {
      return jsonResponse(res, { success: false, message: "Account is not active", statusCode: 403 });
    }

    const valid = bcrypt.compareSync(String(password), user.password_hash);
    if (!valid) {
      return jsonResponse(res, { success: false, message: "Invalid credentials", statusCode: 401 });
    }

    const token = createToken(user.id);
    res.cookie("auth_token", token, {
      httpOnly: true,
      secure: false,
      sameSite: "lax",
      maxAge: 7 * 24 * 60 * 60 * 1000,
    });

    return jsonResponse(res, {
      success: true,
      message: "Login successful",
      data: { token, user: userToDict(user, true) },
    });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Login failed", statusCode: 500 });
  }
});

app.post("/api/logout", (_req, res) => {
  res.clearCookie("auth_token");
  return jsonResponse(res, { success: true, message: "Logged out successfully" });
});

app.get("/api/user", authRequired, (req, res) =>
  jsonResponse(res, {
    success: true,
    message: "User data retrieved successfully",
    data: { user: userToDict(req.user, true) },
  }),
);

app.get("/api/progress", authRequired, (req, res) => {
  try {
    const matches = db.prepare("SELECT * FROM matches WHERE user_id = ? ORDER BY date_uploaded DESC").all(req.user.id);
    const matchesPlayed = matches.length;
    const totalPoints = Number(req.user.total_score || 0);
    const wins = matches.filter((m) => Number(m.goals || 0) > 0).length;
    const losses = matchesPlayed - wins;
    const avgScore = matchesPlayed ? matches.reduce((sum, m) => sum + Number(m.match_score || 0), 0) / matchesPlayed : 0;
    const totalGoals = matches.reduce((sum, m) => sum + Number(m.goals || 0), 0);
    const recentMatches = matches.slice(0, 5).map(matchToDict);
    const winRate = matchesPlayed ? Math.round((wins / matchesPlayed) * 100) : 0;
    const seasonProgress = Math.min(Math.round((matchesPlayed / 50) * 100), 100);

    return jsonResponse(res, {
      success: true,
      message: "Progress retrieved successfully",
      data: {
        matches_played: matchesPlayed,
        wins,
        losses,
        total_points: totalPoints,
        average_score: Number(avgScore.toFixed(2)),
        win_rate: winRate,
        recent_matches: recentMatches,
        total_goals: totalGoals,
        season_progress: seasonProgress,
      },
    });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to retrieve progress", statusCode: 500 });
  }
});

app.get("/api/leaderboard", (req, res) => {
  try {
    const limit = Math.max(1, Number(req.query.limit || 10));
    const users = db
      .prepare(
        "SELECT u.id, u.username, u.total_score, (SELECT COUNT(*) FROM matches m WHERE m.user_id = u.id) AS matches_played FROM users u WHERE u.is_active = 1 AND u.is_banned = 0 ORDER BY u.total_score DESC, u.id ASC LIMIT ?",
      )
      .all(limit);

    const leaderboard = users.map((u, index) => ({
      rank: index + 1,
      user_id: u.id,
      username: u.username,
      total_score: Number(u.total_score || 0),
      matches_played: Number(u.matches_played || 0),
    }));

    return jsonResponse(res, {
      success: true,
      message: "Leaderboard retrieved successfully",
      data: { leaderboard },
    });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to retrieve leaderboard", statusCode: 500 });
  }
});

app.get("/api/leaderboard/:userId", (req, res) => {
  try {
    const userId = Number(req.params.userId);
    const user = db.prepare("SELECT * FROM users WHERE id = ?").get(userId);
    if (!user) {
      return jsonResponse(res, { success: false, message: "User not found", statusCode: 404 });
    }

    const higherScoreCount = db
      .prepare("SELECT COUNT(*) AS count FROM users WHERE total_score > ? AND is_active = 1 AND is_banned = 0")
      .get(user.total_score).count;
    const matchCount = db.prepare("SELECT COUNT(*) AS count FROM matches WHERE user_id = ?").get(userId).count;
    const totalPlayers = db.prepare("SELECT COUNT(*) AS count FROM users WHERE is_active = 1 AND is_banned = 0").get()
      .count;

    return jsonResponse(res, {
      success: true,
      message: "User rank retrieved successfully",
      data: {
        user_id: user.id,
        username: user.username,
        rank: Number(higherScoreCount) + 1,
        total_score: Number(user.total_score || 0),
        matches_played: Number(matchCount || 0),
        total_players: Number(totalPlayers || 0),
      },
    });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to retrieve user rank", statusCode: 500 });
  }
});

app.get("/api/notifications", authRequired, (req, res) => {
  try {
    const limit = Math.max(1, Number(req.query.limit || 20));
    const unreadOnly = String(req.query.unread_only || "false").toLowerCase() === "true";
    let rows = db
      .prepare("SELECT * FROM notifications WHERE user_id = ? ORDER BY date_created DESC LIMIT ?")
      .all(req.user.id, limit);

    if (unreadOnly) rows = rows.filter((n) => !normalizeBool(n.is_read));
    const unreadCount = rows.filter((n) => !normalizeBool(n.is_read)).length;

    return jsonResponse(res, {
      success: true,
      message: "Notifications retrieved successfully",
      data: {
        notifications: rows.map(notificationToDict),
        unread_count: unreadCount,
      },
    });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to retrieve notifications", statusCode: 500 });
  }
});

app.put("/api/notifications/:notificationId/read", authRequired, (req, res) => {
  try {
    const notificationId = Number(req.params.notificationId);
    const notification = db
      .prepare("SELECT * FROM notifications WHERE id = ? AND user_id = ? LIMIT 1")
      .get(notificationId, req.user.id);

    if (!notification) {
      return jsonResponse(res, { success: false, message: "Notification not found", statusCode: 404 });
    }

    db.prepare("UPDATE notifications SET is_read = 1 WHERE id = ?").run(notificationId);
    return jsonResponse(res, { success: true, message: "Notification marked as read" });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to mark notification as read", statusCode: 500 });
  }
});

app.delete("/api/notifications/:notificationId", authRequired, (req, res) => {
  try {
    const notificationId = Number(req.params.notificationId);
    const notification = db
      .prepare("SELECT id FROM notifications WHERE id = ? AND user_id = ? LIMIT 1")
      .get(notificationId, req.user.id);

    if (!notification) {
      return jsonResponse(res, { success: false, message: "Notification not found", statusCode: 404 });
    }

    db.prepare("DELETE FROM notifications WHERE id = ?").run(notificationId);
    return jsonResponse(res, { success: true, message: "Notification deleted successfully" });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to delete notification", statusCode: 500 });
  }
});

app.get("/api/admin/stats", adminRequired, (_req, res) => {
  try {
    const usersTotal = Number(db.prepare("SELECT COUNT(*) AS count FROM users").get().count || 0);
    const usersActive = Number(
      db.prepare("SELECT COUNT(*) AS count FROM users WHERE is_active = 1 AND is_banned = 0").get().count || 0,
    );
    const usersBanned = Number(db.prepare("SELECT COUNT(*) AS count FROM users WHERE is_banned = 1").get().count || 0);
    const usersInactive = Math.max(usersTotal - usersActive - usersBanned, 0);

    const matchesTotal = Number(db.prepare("SELECT COUNT(*) AS count FROM matches").get().count || 0);
    const matchesToday = Number(
      db.prepare("SELECT COUNT(*) AS count FROM matches WHERE DATE(date_uploaded) = DATE('now')").get().count || 0,
    );
    const matchesPending = Number(db.prepare("SELECT COUNT(*) AS count FROM matches WHERE is_verified = 0").get().count || 0);
    const matchesVerified = Number(
      db.prepare("SELECT COUNT(*) AS count FROM matches WHERE is_verified = 1").get().count || 0,
    );

    const competitionsTotal = Number(db.prepare("SELECT COUNT(*) AS count FROM competitions").get().count || 0);
    const competitionsActive = Number(
      db.prepare("SELECT COUNT(*) AS count FROM competitions WHERE status = 'active'").get().count || 0,
    );
    const competitionsUpcoming = Number(
      db.prepare("SELECT COUNT(*) AS count FROM competitions WHERE status = 'upcoming'").get().count || 0,
    );
    const competitionsFinished = Number(
      db.prepare("SELECT COUNT(*) AS count FROM competitions WHERE status = 'finished'").get().count || 0,
    );

    return jsonResponse(res, {
      success: true,
      message: "Admin stats retrieved successfully",
      data: {
        users: { total: usersTotal, active: usersActive, inactive: usersInactive, banned: usersBanned },
        matches: { total: matchesTotal, today: matchesToday, pending: matchesPending, verified: matchesVerified },
        competitions: {
          total: competitionsTotal,
          active: competitionsActive,
          upcoming: competitionsUpcoming,
          finished: competitionsFinished,
        },
      },
    });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to retrieve admin stats", statusCode: 500 });
  }
});

app.get("/api/admin/users", adminRequired, (req, res) => {
  try {
    const search = String(req.query.search || "").trim();
    const status = String(req.query.status || "").trim().toLowerCase();

    const conditions = [];
    const params = [];

    if (status === "active") conditions.push("is_active = 1 AND is_banned = 0");
    if (status === "inactive") conditions.push("is_active = 0 AND is_banned = 0");
    if (status === "banned") conditions.push("is_banned = 1");

    if (search) {
      conditions.push("(username LIKE ? OR email LIKE ?)");
      params.push(`%${search}%`, `%${search}%`);
    }

    const whereClause = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";
    const rows = db
      .prepare(
        `SELECT id, username, email, total_score, matches_played, is_active, is_admin, is_banned, created_at
         FROM users ${whereClause}
         ORDER BY total_score DESC, id ASC`,
      )
      .all(...params);

    return jsonResponse(res, {
      success: true,
      message: "Users retrieved successfully",
      data: { users: rows.map((u) => userToDict(u, true)) },
    });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to retrieve users", statusCode: 500 });
  }
});

app.post("/api/admin/users/:userId/deactivate", adminRequired, (req, res) => {
  try {
    const userId = Number(req.params.userId);
    if (userId === req.user.id) {
      return jsonResponse(res, { success: false, message: "You cannot deactivate your own account", statusCode: 400 });
    }
    const result = db.prepare("UPDATE users SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?").run(userId);
    if (!result.changes) return jsonResponse(res, { success: false, message: "User not found", statusCode: 404 });
    createNotification(userId, "Your account has been deactivated by an admin.", "Account Update", "warning");
    return jsonResponse(res, { success: true, message: "User deactivated successfully" });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to deactivate user", statusCode: 500 });
  }
});

app.post("/api/admin/users/:userId/ban", adminRequired, (req, res) => {
  try {
    const userId = Number(req.params.userId);
    if (userId === req.user.id) {
      return jsonResponse(res, { success: false, message: "You cannot ban your own account", statusCode: 400 });
    }
    const result = db
      .prepare("UPDATE users SET is_banned = 1, is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?")
      .run(userId);
    if (!result.changes) return jsonResponse(res, { success: false, message: "User not found", statusCode: 404 });
    createNotification(userId, "Your account has been banned by an admin.", "Account Update", "danger");
    return jsonResponse(res, { success: true, message: "User banned successfully" });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to ban user", statusCode: 500 });
  }
});

app.post("/api/admin/users/:userId/activate", adminRequired, (req, res) => {
  try {
    const userId = Number(req.params.userId);
    const result = db
      .prepare("UPDATE users SET is_active = 1, is_banned = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?")
      .run(userId);
    if (!result.changes) return jsonResponse(res, { success: false, message: "User not found", statusCode: 404 });
    createNotification(userId, "Your account has been reactivated by an admin.", "Account Update", "success");
    return jsonResponse(res, { success: true, message: "User activated successfully" });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to activate user", statusCode: 500 });
  }
});

app.get("/api/admin/matches", adminRequired, (req, res) => {
  try {
    const search = String(req.query.search || "").trim();
    const status = String(req.query.status || "").trim().toLowerCase();
    const competitionId = String(req.query.competition_id || "").trim();
    const date = String(req.query.date || "").trim();

    const conditions = [];
    const params = [];

    if (search) {
      conditions.push("(u.username LIKE ? OR u.email LIKE ?)");
      params.push(`%${search}%`, `%${search}%`);
    }
    if (status === "verified") conditions.push("m.is_verified = 1");
    if (status === "pending") conditions.push("m.is_verified = 0");
    if (status === "rejected") conditions.push("m.rejection_reason IS NOT NULL");
    if (competitionId) {
      conditions.push("m.competition_id = ?");
      params.push(Number(competitionId));
    }
    if (date) {
      conditions.push("DATE(m.date_uploaded) = DATE(?)");
      params.push(date);
    }

    const whereClause = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";
    const rows = db
      .prepare(
        `SELECT m.*, u.username, u.email
         FROM matches m
         LEFT JOIN users u ON u.id = m.user_id
         ${whereClause}
         ORDER BY m.date_uploaded DESC`,
      )
      .all(...params);

    return jsonResponse(res, {
      success: true,
      message: "Matches retrieved successfully",
      data: {
        matches: rows.map((m) => ({
          ...matchToDict(m),
          username: m.username,
          email: m.email,
        })),
      },
    });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to retrieve matches", statusCode: 500 });
  }
});

app.get("/api/admin/matches/:matchId", adminRequired, (req, res) => {
  try {
    const matchId = Number(req.params.matchId);
    const match = db
      .prepare(
        `SELECT m.*, u.username, u.email
         FROM matches m
         LEFT JOIN users u ON u.id = m.user_id
         WHERE m.id = ?
         LIMIT 1`,
      )
      .get(matchId);

    if (!match) return jsonResponse(res, { success: false, message: "Match not found", statusCode: 404 });

    return jsonResponse(res, {
      success: true,
      message: "Match retrieved successfully",
      data: {
        match: { ...matchToDict(match), username: match.username, email: match.email },
        stats: {
          goals: match.goals,
          assists: match.assists,
          possession: match.possession,
          shots: match.shots,
          shots_on_target: match.shots_on_target,
          pass_accuracy: match.pass_accuracy,
          tackles: match.tackles,
        },
      },
    });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to retrieve match", statusCode: 500 });
  }
});

app.post("/api/admin/matches/:matchId/verify", adminRequired, (req, res) => {
  try {
    const matchId = Number(req.params.matchId);
    const match = db.prepare("SELECT * FROM matches WHERE id = ? LIMIT 1").get(matchId);
    if (!match) return jsonResponse(res, { success: false, message: "Match not found", statusCode: 404 });

    db.prepare("UPDATE matches SET is_verified = 1, rejection_reason = NULL WHERE id = ?").run(matchId);
    createNotification(match.user_id, "Your match has been verified by an admin.", "Match Verified", "success");
    return jsonResponse(res, { success: true, message: "Match verified successfully" });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to verify match", statusCode: 500 });
  }
});

app.post("/api/admin/matches/:matchId/reject", adminRequired, (req, res) => {
  try {
    const matchId = Number(req.params.matchId);
    const reason = String(req.body?.reason || "Rejected by admin");
    const match = db.prepare("SELECT * FROM matches WHERE id = ? LIMIT 1").get(matchId);
    if (!match) return jsonResponse(res, { success: false, message: "Match not found", statusCode: 404 });

    db.prepare("UPDATE matches SET is_verified = 0, rejection_reason = ? WHERE id = ?").run(reason, matchId);
    createNotification(match.user_id, `Your match was rejected: ${reason}`, "Match Rejected", "warning");
    return jsonResponse(res, { success: true, message: "Match rejected successfully" });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to reject match", statusCode: 500 });
  }
});

app.get("/api/admin/competitions", adminRequired, (_req, res) => {
  try {
    const competitions = db.prepare("SELECT * FROM competitions ORDER BY created_at DESC, id DESC").all();
    return jsonResponse(res, {
      success: true,
      message: "Competitions retrieved successfully",
      data: {
        competitions: competitions.map((c) => ({
          id: c.id,
          name: c.name,
          description: c.description,
          start_date: c.start_date ? new Date(c.start_date).toISOString() : null,
          end_date: c.end_date ? new Date(c.end_date).toISOString() : null,
          status: c.status || "upcoming",
          created_at: c.created_at ? new Date(c.created_at).toISOString() : null,
        })),
      },
    });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to retrieve competitions", statusCode: 500 });
  }
});

app.put("/api/admin/competitions/:competitionId", adminRequired, (req, res) => {
  try {
    const competitionId = Number(req.params.competitionId);
    const existing = db.prepare("SELECT * FROM competitions WHERE id = ? LIMIT 1").get(competitionId);
    if (!existing) return jsonResponse(res, { success: false, message: "Competition not found", statusCode: 404 });

    const name = req.body?.name ?? existing.name;
    const description = req.body?.description ?? existing.description;
    const startDate = req.body?.start_date || null;
    const endDate = req.body?.end_date || null;
    const status = req.body?.status || existing.status || "upcoming";

    db.prepare(
      "UPDATE competitions SET name = ?, description = ?, start_date = ?, end_date = ?, status = ? WHERE id = ?",
    ).run(name, description, startDate, endDate, status, competitionId);

    return jsonResponse(res, { success: true, message: "Competition updated successfully" });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to update competition", statusCode: 500 });
  }
});

app.post("/api/admin/competitions/:competitionId/start", adminRequired, (req, res) => {
  try {
    const competitionId = Number(req.params.competitionId);
    const result = db
      .prepare("UPDATE competitions SET status = 'active', start_date = COALESCE(start_date, CURRENT_TIMESTAMP) WHERE id = ?")
      .run(competitionId);
    if (!result.changes) return jsonResponse(res, { success: false, message: "Competition not found", statusCode: 404 });
    return jsonResponse(res, { success: true, message: "Competition started successfully" });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to start competition", statusCode: 500 });
  }
});

app.post("/api/admin/competitions/:competitionId/end", adminRequired, (req, res) => {
  try {
    const competitionId = Number(req.params.competitionId);
    const result = db
      .prepare("UPDATE competitions SET status = 'finished', end_date = COALESCE(end_date, CURRENT_TIMESTAMP) WHERE id = ?")
      .run(competitionId);
    if (!result.changes) return jsonResponse(res, { success: false, message: "Competition not found", statusCode: 404 });
    return jsonResponse(res, { success: true, message: "Competition ended successfully" });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to end competition", statusCode: 500 });
  }
});

app.get("/api/admin/notifications", adminRequired, (req, res) => {
  try {
    const limit = Math.max(1, Number(req.query.limit || 50));
    const rows = db
      .prepare("SELECT * FROM notifications WHERE user_id = ? ORDER BY date_created DESC LIMIT ?")
      .all(req.user.id, limit);
    const unreadCount = rows.filter((n) => !normalizeBool(n.is_read)).length;
    return jsonResponse(res, {
      success: true,
      message: "Notifications retrieved successfully",
      data: { notifications: rows.map(notificationToDict), unread_count: unreadCount },
    });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to retrieve notifications", statusCode: 500 });
  }
});

app.delete("/api/admin/notifications/:notificationId", adminRequired, (req, res) => {
  try {
    const notificationId = Number(req.params.notificationId);
    const notification = db
      .prepare("SELECT id FROM notifications WHERE id = ? AND user_id = ? LIMIT 1")
      .get(notificationId, req.user.id);

    if (!notification) {
      return jsonResponse(res, { success: false, message: "Notification not found", statusCode: 404 });
    }

    db.prepare("DELETE FROM notifications WHERE id = ?").run(notificationId);
    return jsonResponse(res, { success: true, message: "Notification deleted successfully" });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to delete notification", statusCode: 500 });
  }
});

app.post("/api/admin/announcements", adminRequired, (req, res) => {
  try {
    const title = String(req.body?.title || "Announcement").trim();
    const message = String(req.body?.message || "").trim();
    const recipients = String(req.body?.recipients || "all").trim().toLowerCase();
    const specificUsername = String(req.body?.specific_username || "").trim();

    if (!message) return jsonResponse(res, { success: false, message: "Message is required", statusCode: 400 });

    let targetUsers = [];
    if (recipients === "active") {
      targetUsers = db.prepare("SELECT id FROM users WHERE is_admin = 0 AND is_active = 1 AND is_banned = 0").all();
    } else if (recipients === "specific" && specificUsername) {
      targetUsers = db
        .prepare("SELECT id FROM users WHERE is_admin = 0 AND username = ? LIMIT 1")
        .all(specificUsername);
    } else if (recipients === "specific" && !specificUsername) {
      return jsonResponse(res, {
        success: false,
        message: "Specific username is required for this recipient option",
        statusCode: 400,
      });
    } else {
      targetUsers = db.prepare("SELECT id FROM users WHERE is_admin = 0").all();
    }

    const tx = db.transaction(() => {
      for (const target of targetUsers) {
        createNotification(target.id, message, title, "info");
      }
    });
    tx();

    createNotification(req.user.id, `Announcement sent to ${targetUsers.length} user(s).`, "Announcement Sent", "success");

    return jsonResponse(res, {
      success: true,
      message: "Announcement sent successfully",
      data: { sent_count: targetUsers.length },
    });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to send announcement", statusCode: 500 });
  }
});

app.get("/api/admin/ai-status", adminRequired, (_req, res) => {
  try {
    return jsonResponse(res, {
      success: true,
      message: "AI key status retrieved successfully",
      data: apiKeyManager.getUsageStats(),
    });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to retrieve AI key status", statusCode: 500 });
  }
});

app.post("/api/admin/ai-keys", adminRequired, (req, res) => {
  try {
    const keyInput = String(req.body?.key || "").trim();
    if (!keyInput) {
      return jsonResponse(res, { success: false, message: "API key is required", statusCode: 400 });
    }

    const added = apiKeyManager.addKey(keyInput);
    if (!added) {
      return jsonResponse(res, { success: false, message: "API key already exists", statusCode: 400 });
    }

    persistApiKeysToEnv();

    return jsonResponse(res, {
      success: true,
      message: "API key added successfully",
      data: apiKeyManager.getUsageStats(),
    });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to add API key", statusCode: 500 });
  }
});

app.post("/api/admin/ai-keys/reload", adminRequired, (_req, res) => {
  try {
    require("dotenv").config({ path: ENV_PATH, override: true });
    apiKeyManager.reloadFromEnv();
    return jsonResponse(res, {
      success: true,
      message: "AI keys reloaded from .env",
      data: apiKeyManager.getUsageStats(),
    });
  } catch (_err) {
    return jsonResponse(res, { success: false, message: "Failed to reload AI keys", statusCode: 500 });
  }
});

// Upload endpoint: duplicate check -> AI extraction -> score -> leaderboard + notifications update.
app.post("/api/upload", authRequired, (req, res) => {
  upload.single("file")(req, res, async (err) => {
    if (err) {
      return jsonResponse(res, { success: false, message: err.message || "Upload failed", statusCode: 400 });
    }
    if (!req.file) {
      return jsonResponse(res, { success: false, message: "No file provided", statusCode: 400 });
    }

    try {
      const competitionId = req.body?.competition_id ? Number(req.body.competition_id) : null;
      const imagePath = req.file.path;
      const imageHash = calculateImageHash(imagePath);
      const duplicate = db.prepare("SELECT id FROM matches WHERE image_hash = ? LIMIT 1").get(imageHash);

      if (duplicate) {
        fs.unlinkSync(imagePath);
        return jsonResponse(res, {
          success: false,
          message: "Duplicate screenshot detected! This image has already been uploaded.",
          statusCode: 400,
        });
      }

      const aiResult = await analyzeScreenshotWithGemini(imagePath);
      if (!aiResult.success) {
        fs.unlinkSync(imagePath);
        return jsonResponse(res, {
          success: false,
          message: "AI validation unavailable. No points awarded.",
          statusCode: 503,
          data: { score: 0, error: aiResult.error || "AI unavailable" },
        });
      }

      if (!aiResult.is_valid_screenshot) {
        fs.unlinkSync(imagePath);
        return jsonResponse(res, {
          success: false,
          message: "Screenshot does not contain valid match statistics. No points awarded.",
          statusCode: 400,
          data: { score: 0 },
        });
      }

      const scoreResult = calculateScoreFromAI(aiResult);
      const matchScore = scoreResult.total_score;
      const stats = {
        goals: Number(aiResult.goals || 0),
        assists: Number(aiResult.assists || 0),
        possession: Number(aiResult.possession || 0),
        shots: Number(aiResult.shots || 0),
        shots_on_target: Number(aiResult.shots_on_target || 0),
        pass_accuracy: Number(aiResult.pass_accuracy || 0),
        tackles: Number(aiResult.tackles || 0),
      };

      const tx = db.transaction(() => {
        const matchResult = db
          .prepare(
            "INSERT INTO matches (user_id, image_filename, image_hash, match_score, goals, assists, possession, shots, shots_on_target, pass_accuracy, tackles, competition_id, is_verified, date_uploaded) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)",
          )
          .run(
            req.user.id,
            req.file.filename,
            imageHash,
            matchScore,
            stats.goals,
            stats.assists,
            stats.possession,
            stats.shots,
            stats.shots_on_target,
            stats.pass_accuracy,
            stats.tackles,
            competitionId,
          );

        db.prepare(
          "UPDATE users SET total_score = total_score + ?, matches_played = matches_played + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        ).run(matchScore, req.user.id);

        createNotification(
          req.user.id,
          `Congratulations! You scored ${matchScore} points. Goals: ${stats.goals}, Possession: ${stats.possession}%`,
          "Match Processed",
          "success",
        );

        return matchResult.lastInsertRowid;
      });

      const matchId = tx();
      const refreshedUser = db.prepare("SELECT * FROM users WHERE id = ?").get(req.user.id);
      return jsonResponse(res, {
        success: true,
        message: `Congratulations! You scored ${matchScore} points`,
        data: {
          match_id: matchId,
          match_score: matchScore,
          stats,
          score_breakdown: scoreResult.score_breakdown,
          total_score: Number(refreshedUser.total_score || 0),
          is_valid_screenshot: true,
          is_fallback: Boolean(aiResult.is_fallback),
        },
      });
    } catch (_error) {
      return jsonResponse(res, { success: false, message: "Upload failed", statusCode: 500 });
    }
  });
});

app.use((err, _req, res, _next) => {
  if (err && String(err.message || "").includes("CORS")) {
    return res.status(403).json({ success: false, message: "CORS blocked this origin" });
  }
  return res.status(500).json({ success: false, message: "Internal server error" });
});

app.listen(PORT, () => {
  console.log("FIFA Stats Platform API (Express)");
  console.log(`Server running at: http://localhost:${PORT}`);
});
