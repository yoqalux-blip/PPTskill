#!/usr/bin/env node

import fs from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const drawioServerScript = path.resolve(root, "node_modules", "@drawio", "mcp", "src", "index.js");

function parseArgs(argv) {
  const [command, ...rest] = argv;
  const options = {};

  for (let index = 0; index < rest.length; index += 1) {
    const token = rest[index];
    if (!token.startsWith("--")) {
      continue;
    }
    const key = token.slice(2);
    const next = rest[index + 1];
    if (!next || next.startsWith("--")) {
      options[key] = true;
      continue;
    }
    options[key] = next;
    index += 1;
  }

  return { command, options };
}

function usage() {
  console.log(
    [
      "Usage:",
      "  node ./scripts/drawio_mcp_client.mjs list-tools [--output-file path]",
      "  node ./scripts/drawio_mcp_client.mjs open-xml --content-file path [--response-file path] [--dark auto|true|false] [--lightbox]",
      "  node ./scripts/drawio_mcp_client.mjs open-mermaid --content-file path [--response-file path] [--dark auto|true|false] [--lightbox]",
      "  node ./scripts/drawio_mcp_client.mjs open-csv --content-file path [--response-file path] [--dark auto|true|false] [--lightbox]",
    ].join("\n"),
  );
}

function asBool(value) {
  return value === true || value === "true" || value === "1";
}

function extractUrl(result) {
  const textParts = (result.content || [])
    .filter((item) => item.type === "text")
    .map((item) => item.text)
    .join("\n");
  const match = textParts.match(/https?:\/\/\S+/);
  return match ? match[0] : null;
}

async function buildClient() {
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: [drawioServerScript],
    cwd: root,
    stderr: "pipe",
  });
  const client = new Client(
    { name: "paper-to-defense-ppt-drawio-client", version: "0.1.0" },
    { capabilities: {} },
  );
  await client.connect(transport);
  return { client, transport };
}

async function closeClient(transport) {
  try {
    await transport.close();
  } catch {
    // Ignore shutdown noise from the child process.
  }
}

async function writeMaybe(pathname, payload) {
  if (!pathname) {
    return;
  }
  await fs.mkdir(path.dirname(pathname), { recursive: true });
  await fs.writeFile(pathname, JSON.stringify(payload, null, 2), "utf8");
}

async function readContent(options) {
  if (typeof options["content-file"] === "string") {
    return fs.readFile(path.resolve(options["content-file"]), "utf8");
  }
  if (typeof options.content === "string") {
    return options.content;
  }
  throw new Error("Missing --content-file or --content.");
}

async function main() {
  const { command, options } = parseArgs(process.argv.slice(2));

  if (!command || options.help) {
    usage();
    process.exit(command ? 0 : 1);
  }

  const { client, transport } = await buildClient();

  try {
    if (command === "list-tools") {
      const result = await client.listTools();
      await writeMaybe(options["output-file"], result);
      console.log(`draw.io MCP tools: ${(result.tools || []).map((tool) => tool.name).join(", ")}`);
      return;
    }

    const toolNameByCommand = {
      "open-xml": "open_drawio_xml",
      "open-mermaid": "open_drawio_mermaid",
      "open-csv": "open_drawio_csv",
    };
    const toolName = toolNameByCommand[command];

    if (!toolName) {
      usage();
      process.exit(1);
    }

    const content = await readContent(options);
    const result = await client.callTool({
      name: toolName,
      arguments: {
        content,
        dark: typeof options.dark === "string" ? options.dark : "auto",
        lightbox: asBool(options.lightbox),
      },
    });
    const response = {
      tool: toolName,
      url: extractUrl(result),
      result,
    };
    await writeMaybe(options["response-file"], response);
    if (response.url) {
      console.log(`draw.io editor opened: ${response.url}`);
    } else {
      console.log(JSON.stringify(response, null, 2));
    }
  } finally {
    await closeClient(transport);
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exit(1);
});
