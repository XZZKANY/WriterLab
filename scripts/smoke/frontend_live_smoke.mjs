import fs from "node:fs";
import http from "node:http";
import https from "node:https";
import path from "node:path";

const siteBase = new URL(process.argv[2] || "http://127.0.0.1:3000");
const reportPath = process.argv[3] || "";

const commonMarkers = [
  "WriterLab",
];

const routeMatrix = [
  {
    path: "/editor",
    requireCommonMarkers: true,
    requiredMarkers: ["写作台与分支工作区", "分析与一致性", "记忆上下文与 VN 导出"],
  },
  {
    path: "/project",
    requireCommonMarkers: true,
    requiredMarkers: ["Projects", "New project", "Search projects...", "Activity"],
  },
  {
    path: "/project/new",
    requireCommonMarkers: true,
    requiredMarkers: [
      "Create a personal project",
      "What are you working on?",
      "Name your project",
      "Create project",
    ],
  },
  {
    path: "/lore",
    requireCommonMarkers: true,
    requiredMarkers: ["设定库", "项目上下文", "设定摘要"],
  },
  {
    path: "/runtime",
    requireCommonMarkers: true,
    requiredMarkers: ["运行时就绪度", "运行时自检告警"],
  },
  {
    path: "/settings",
    requireCommonMarkers: true,
    requiredMarkers: ["Provider 配置"],
  },
];

if (!/^https?:$/.test(siteBase.protocol)) {
  console.error(`Only http:// or https:// URLs are supported. Received: ${siteBase.href}`);
  process.exit(1);
}

function writeReport(report) {
  if (!reportPath) return;
  fs.mkdirSync(path.dirname(reportPath), { recursive: true });
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf8");
}

function requestPage(url) {
  const client = url.protocol === "https:" ? https : http;
  return new Promise((resolve, reject) => {
    const request = client.request(
      url,
      {
        method: "GET",
        headers: {
          Accept: "text/html",
        },
      },
      (response) => {
        const chunks = [];
        response.on("data", (chunk) => chunks.push(chunk));
        response.on("end", () => {
          resolve({
            statusCode: response.statusCode ?? null,
            statusMessage: response.statusMessage ?? "",
            body: Buffer.concat(chunks).toString("utf8"),
          });
        });
      },
    );
    request.on("error", reject);
    request.end();
  });
}

async function checkRoute(routeConfig) {
  const url = new URL(routeConfig.path, siteBase);
  const response = await requestPage(url);
  const body = response.body;
  const hasHtml = /<!doctype html>|<html/i.test(body);
  const missingCommonMarkers = routeConfig.requireCommonMarkers
    ? commonMarkers.filter((marker) => !body.includes(marker))
    : [];
  const missingRouteMarkers = routeConfig.requiredMarkers.filter((marker) => !body.includes(marker));

  return {
    path: routeConfig.path,
    url: url.href,
    statusCode: response.statusCode,
    statusMessage: response.statusMessage,
    hasHtml,
    missingCommonMarkers,
    missingRouteMarkers,
    ok:
      response.statusCode === 200 &&
      hasHtml &&
      missingCommonMarkers.length === 0 &&
      missingRouteMarkers.length === 0,
  };
}

async function main() {
  const report = {
    checkedAt: new Date().toISOString(),
    baseUrl: siteBase.origin,
    ok: true,
    routes: [],
  };

  for (const routeConfig of routeMatrix) {
    try {
      const routeReport = await checkRoute(routeConfig);
      report.routes.push(routeReport);
    } catch (error) {
      report.routes.push({
        path: routeConfig.path,
        url: new URL(routeConfig.path, siteBase).href,
        ok: false,
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  report.ok = report.routes.every((item) => item.ok);
  writeReport(report);

  if (!report.ok) {
    const failures = report.routes
      .filter((item) => !item.ok)
      .map((item) => {
        if (item.error) {
          return `${item.path}: ${item.error}`;
        }
        const parts = [];
        if (item.statusCode !== 200) {
          parts.push(`HTTP ${item.statusCode ?? "unknown"}`);
        }
        if (!item.hasHtml) {
          parts.push("未返回 HTML");
        }
        if (item.missingCommonMarkers?.length) {
          parts.push(`缺少通用标记: ${item.missingCommonMarkers.join(", ")}`);
        }
        if (item.missingRouteMarkers?.length) {
          parts.push(`缺少路由标记: ${item.missingRouteMarkers.join(", ")}`);
        }
        return `${item.path}: ${parts.join(" | ")}`;
      });
    console.error(`Frontend live smoke failed:\n- ${failures.join("\n- ")}`);
    process.exit(1);
  }

  console.log(`Frontend live smoke passed for ${routeMatrix.length} routes. Report: ${reportPath || "(not written)"}`);
}

await main();
