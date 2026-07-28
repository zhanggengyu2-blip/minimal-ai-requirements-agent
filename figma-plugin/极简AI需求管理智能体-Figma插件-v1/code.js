const COLORS = {
  page: "#F7F8FA",
  surface: "#FFFFFF",
  surfaceMuted: "#F5F6F7",
  border: "#E5E6EB",
  borderStrong: "#D0D3D8",
  text: "#1F2329",
  textSecondary: "#646A73",
  textMuted: "#8F959E",
  blue: "#3370FF",
  blueSoft: "#E8F3FF",
  amber: "#D46B08",
  amberSoft: "#FFF6E8",
  green: "#159957",
  greenSoft: "#EAF8F0",
  red: "#D83931",
  redSoft: "#FDEDEC",
  grayTag: "#EEF0F2",
};

const PRIORITIES = {
  P0: { text: "#C92A24", bg: "#FDE7E6" },
  P1: { text: "#C45A0A", bg: "#FFF0DE" },
  P2: { text: "#245BDB", bg: "#E8F0FF" },
  P3: { text: "#59616B", bg: "#EEF0F2" },
};

const LANES = [
  {
    name: "待采纳",
    count: 8,
    color: COLORS.amber,
    bg: COLORS.amberSoft,
    cards: [
      ["REQ-024", "客服工作台支持批量导入客户信息，并自动识别重复客户", "陈晨", "陈", "P0"],
      ["REQ-015", "会话列表增加未读消息聚合与快捷筛选", "林晓", "林", "P1"],
      ["REQ-031", "客户标签支持批量编辑", "王宇", "王", "P2"],
      ["REQ-039", "支持多语言切换并保留用户上次选择", "李娜", "李", "P3"],
    ],
  },
  {
    name: "已采纳",
    count: 6,
    color: COLORS.blue,
    bg: "#EEF4FF",
    cards: [
      ["REQ-002", "修复高峰期消息发送延迟问题", "林晓", "林", "P0"],
      ["REQ-007", "增加历史会话导出能力", "陈晨", "陈", "P1"],
      ["REQ-013", "优化会话搜索相关性排序", "王宇", "王", "P2"],
      ["REQ-018", "会话窗口支持字体大小自定义", "李娜", "李", "P3"],
    ],
  },
  {
    name: "已实现",
    count: 7,
    color: COLORS.green,
    bg: COLORS.greenSoft,
    cards: [
      ["REQ-001", "智能客服机器人自动识别意图并推荐解决方案", "林晓", "林", "P0"],
      ["REQ-004", "知识库支持多级目录与全文检索", "陈晨", "陈", "P1"],
      ["REQ-009", "工单支持自定义字段与流程", "王宇", "王", "P2"],
      ["REQ-014", "消息通知支持邮件与站内信", "李娜", "李", "P3"],
    ],
  },
  {
    name: "不采纳",
    count: 3,
    color: COLORS.red,
    bg: COLORS.redSoft,
    cards: [
      ["REQ-006", "第三方视频通话与产品定位不符", "林晓", "林", "P0"],
      ["REQ-017", "自定义聊天气泡样式投入产出比低", "陈晨", "陈", "P1"],
      ["REQ-022", "游戏化任务系统属于非核心需求", "王宇", "王", "P2"],
    ],
  },
];

const PROJECTS = [
  ["智能客服平台", 24, true],
  ["数据中台", 18, false],
  ["移动端重构", 11, false],
  ["官网增长项目", 9, false],
];

function rgb(hex) {
  const clean = hex.replace("#", "");
  return {
    r: parseInt(clean.slice(0, 2), 16) / 255,
    g: parseInt(clean.slice(2, 4), 16) / 255,
    b: parseInt(clean.slice(4, 6), 16) / 255,
  };
}

function solid(hex, opacity = 1) {
  return { type: "SOLID", color: rgb(hex), opacity };
}

function setFill(node, hex, opacity = 1) {
  node.fills = [solid(hex, opacity)];
}

function setStroke(node, hex, weight = 1) {
  node.strokes = [solid(hex)];
  node.strokeWeight = weight;
  node.strokeAlign = "INSIDE";
}

function uniquePageName(base) {
  const names = new Set(figma.root.children.map((page) => page.name));
  if (!names.has(base)) return base;
  let index = 2;
  while (names.has(`${base} ${index}`)) index += 1;
  return `${base} ${index}`;
}

function autoFrame(name, direction, width, height) {
  const frame = figma.createFrame();
  frame.name = name;
  frame.resize(width, height);
  frame.layoutMode = direction;
  frame.primaryAxisSizingMode = "FIXED";
  frame.counterAxisSizingMode = "FIXED";
  frame.primaryAxisAlignItems = "MIN";
  frame.counterAxisAlignItems = "MIN";
  frame.clipsContent = false;
  frame.fills = [];
  return frame;
}

function makeText(value, size = 14, weight = "Regular", color = COLORS.text, width = null) {
  const text = figma.createText();
  text.name = "Text";
  text.fontName = { family: FONT_FAMILY, style: weight };
  text.fontSize = size;
  text.lineHeight = { unit: "PIXELS", value: Math.round(size * 1.55) };
  text.fills = [solid(color)];
  text.characters = value;
  if (width !== null) {
    text.resize(width, Math.max(text.height, size * 1.55));
    text.textAutoResize = "HEIGHT";
  } else {
    text.textAutoResize = "WIDTH_AND_HEIGHT";
  }
  return text;
}

function makeButton(label, kind = "secondary") {
  const button = autoFrame(`Button/${kind}/${label}`, "HORIZONTAL", 100, 36);
  button.primaryAxisSizingMode = "AUTO";
  button.counterAxisSizingMode = "FIXED";
  button.primaryAxisAlignItems = "CENTER";
  button.counterAxisAlignItems = "CENTER";
  button.paddingLeft = 16;
  button.paddingRight = 16;
  button.itemSpacing = 6;
  button.cornerRadius = 6;
  if (kind === "primary") {
    setFill(button, COLORS.blue);
    button.appendChild(makeText(label, 14, "Medium", COLORS.surface));
  } else {
    setFill(button, COLORS.surface);
    setStroke(button, COLORS.borderStrong);
    button.appendChild(makeText(label, 14, "Medium", COLORS.text));
  }
  return button;
}

function makePriorityBadge(priority) {
  const colors = PRIORITIES[priority];
  const badge = autoFrame(`Priority/${priority}`, "HORIZONTAL", 44, 24);
  badge.primaryAxisAlignItems = "CENTER";
  badge.counterAxisAlignItems = "CENTER";
  badge.cornerRadius = 5;
  setFill(badge, colors.bg);
  badge.appendChild(makeText(priority, 12, "Bold", colors.text));
  return badge;
}

function makeAvatar(initial, index = 0) {
  const palette = ["#D9E8FF", "#E6DFFF", "#DDF3E8", "#FFE7D6"];
  const wrap = figma.createFrame();
  wrap.name = `Avatar/${initial}`;
  wrap.resize(24, 24);
  wrap.clipsContent = true;
  wrap.cornerRadius = 12;
  setFill(wrap, palette[index % palette.length]);
  const initialText = makeText(initial, 11, "Medium", COLORS.textSecondary);
  initialText.x = (24 - initialText.width) / 2;
  initialText.y = (24 - initialText.height) / 2;
  wrap.appendChild(initialText);
  return wrap;
}

function makeFolderIcon() {
  const icon = figma.createFrame();
  icon.name = "Icon/Folder";
  icon.resize(18, 14);
  icon.cornerRadius = 2;
  setFill(icon, COLORS.blue);
  const tab = figma.createRectangle();
  tab.name = "Folder Tab";
  tab.resize(8, 4);
  tab.x = 2;
  tab.y = -2;
  tab.cornerRadius = 1;
  setFill(tab, COLORS.blue);
  icon.appendChild(tab);
  return icon;
}

function makeDocumentIcon() {
  const icon = figma.createFrame();
  icon.name = "Icon/Requirement";
  icon.resize(16, 18);
  icon.cornerRadius = 2;
  setFill(icon, COLORS.blueSoft);
  setStroke(icon, COLORS.blue);
  const line1 = figma.createRectangle();
  line1.resize(8, 1);
  line1.x = 4;
  line1.y = 6;
  setFill(line1, COLORS.blue);
  const line2 = figma.createRectangle();
  line2.resize(6, 1);
  line2.x = 4;
  line2.y = 10;
  setFill(line2, COLORS.blue);
  icon.appendChild(line1);
  icon.appendChild(line2);
  return icon;
}

function makeSearch(width) {
  const field = autoFrame("Search/Current Project", "HORIZONTAL", width, 40);
  field.counterAxisAlignItems = "CENTER";
  field.paddingLeft = 12;
  field.paddingRight = 12;
  field.itemSpacing = 8;
  field.cornerRadius = 6;
  setFill(field, COLORS.surface);
  setStroke(field, COLORS.borderStrong);
  field.appendChild(makeText("⌕", 18, "Regular", COLORS.textMuted));
  field.appendChild(makeText("搜索当前项目需求", 14, "Regular", COLORS.textMuted));
  return field;
}

function makeSelect(label, width) {
  const select = autoFrame(`Select/${label}`, "HORIZONTAL", width, 40);
  select.primaryAxisAlignItems = "SPACE_BETWEEN";
  select.counterAxisAlignItems = "CENTER";
  select.paddingLeft = 12;
  select.paddingRight = 12;
  select.cornerRadius = 6;
  setFill(select, COLORS.surface);
  setStroke(select, COLORS.borderStrong);
  select.appendChild(makeText(label, 14, "Regular", COLORS.textSecondary));
  select.appendChild(makeText("▾", 12, "Regular", COLORS.textMuted));
  return select;
}

function createCardComponent(priority) {
  const component = figma.createComponent();
  component.name = `Priority=${priority}`;
  component.resize(245, 132);
  component.layoutMode = "VERTICAL";
  component.primaryAxisSizingMode = "FIXED";
  component.counterAxisSizingMode = "FIXED";
  component.paddingTop = 10;
  component.paddingRight = 12;
  component.paddingBottom = 10;
  component.paddingLeft = 12;
  component.itemSpacing = 7;
  component.cornerRadius = 6;
  setFill(component, COLORS.surface);
  setStroke(component, COLORS.borderStrong);

  const top = autoFrame("Card Header", "HORIZONTAL", 221, 24);
  top.primaryAxisAlignItems = "SPACE_BETWEEN";
  top.counterAxisAlignItems = "CENTER";
  const reqId = makeText("REQ-000", 12, "Regular", COLORS.textSecondary);
  reqId.name = "ReqID";
  top.appendChild(reqId);
  top.appendChild(makePriorityBadge(priority));
  component.appendChild(top);

  const content = makeText("需求内容摘要，两到三行展示需求关键信息", 14, "Regular", COLORS.text, 221);
  content.name = "Content";
  component.appendChild(content);

  const footer = autoFrame("Submitter", "HORIZONTAL", 221, 24);
  footer.counterAxisAlignItems = "CENTER";
  footer.itemSpacing = 8;
  const avatar = makeAvatar("陈", 0);
  avatar.name = "Avatar";
  footer.appendChild(avatar);
  const submitter = makeText("陈晨", 12, "Regular", COLORS.textSecondary);
  submitter.name = "SubmitterName";
  footer.appendChild(submitter);
  component.appendChild(footer);
  return component;
}

function overrideText(instance, nodeName, value) {
  const node = instance.findOne((child) => child.type === "TEXT" && child.name === nodeName);
  if (node) node.characters = value;
}

function overrideAvatar(instance, initial, paletteIndex) {
  const avatar = instance.findOne((child) => child.type === "FRAME" && child.name === "Avatar");
  if (!avatar) return;
  const palette = ["#D9E8FF", "#E6DFFF", "#DDF3E8", "#FFE7D6"];
  setFill(avatar, palette[paletteIndex % palette.length]);
  const label = avatar.findOne((child) => child.type === "TEXT");
  if (label) label.characters = initial;
}

function createCardInstance(componentMap, data, index) {
  const [id, content, submitter, initial, priority] = data;
  const instance = componentMap[priority].createInstance();
  instance.name = `Requirement/${id}`;
  overrideText(instance, "ReqID", id);
  overrideText(instance, "Content", content);
  overrideText(instance, "SubmitterName", submitter);
  overrideAvatar(instance, initial, index);
  return instance;
}

function makeProjectGroup(projectName, count, selected) {
  const group = autoFrame(`Project/${projectName}`, "VERTICAL", 248, 82);
  group.itemSpacing = 6;

  const projectRow = autoFrame("Project Row", "HORIZONTAL", 248, 34);
  projectRow.counterAxisAlignItems = "CENTER";
  projectRow.itemSpacing = 10;
  projectRow.paddingLeft = 8;
  projectRow.paddingRight = 8;
  projectRow.appendChild(makeText("⌄", 13, "Regular", COLORS.textSecondary));
  projectRow.appendChild(makeFolderIcon());
  projectRow.appendChild(makeText(projectName, 14, "Medium", COLORS.text));
  group.appendChild(projectRow);

  const reqRow = autoFrame("Requirement Nav", "HORIZONTAL", 248, 42);
  reqRow.counterAxisAlignItems = "CENTER";
  reqRow.primaryAxisAlignItems = "SPACE_BETWEEN";
  reqRow.paddingLeft = 52;
  reqRow.paddingRight = 12;
  reqRow.cornerRadius = 6;
  if (selected) setFill(reqRow, COLORS.blueSoft);
  const reqLabel = autoFrame("Requirement Label", "HORIZONTAL", 120, 24);
  reqLabel.counterAxisAlignItems = "CENTER";
  reqLabel.itemSpacing = 9;
  reqLabel.appendChild(makeDocumentIcon());
  reqLabel.appendChild(makeText("需求", 14, selected ? "Medium" : "Regular", selected ? COLORS.blue : COLORS.textSecondary));
  reqRow.appendChild(reqLabel);
  reqRow.appendChild(makeText(String(count), 13, "Regular", COLORS.textSecondary));
  group.appendChild(reqRow);
  return group;
}

function makeLane(lane, componentMap, laneIndex) {
  const frame = autoFrame(`Lane/${lane.name}`, "VERTICAL", 269, 648);
  frame.paddingTop = 12;
  frame.paddingRight = 12;
  frame.paddingBottom = 12;
  frame.paddingLeft = 12;
  frame.itemSpacing = 10;
  frame.cornerRadius = 8;
  setFill(frame, lane.bg, 0.76);
  setStroke(frame, COLORS.border);

  const header = autoFrame("Lane Header", "HORIZONTAL", 245, 28);
  header.counterAxisAlignItems = "CENTER";
  header.itemSpacing = 10;
  const marker = figma.createRectangle();
  marker.name = "Status Accent";
  marker.resize(4, 22);
  marker.cornerRadius = 2;
  setFill(marker, lane.color);
  header.appendChild(marker);
  header.appendChild(makeText(lane.name, 16, "Medium", COLORS.text));
  header.appendChild(makeText(String(lane.count), 13, "Regular", COLORS.textSecondary));
  frame.appendChild(header);

  lane.cards.forEach((card, cardIndex) => {
    frame.appendChild(createCardInstance(componentMap, card, laneIndex + cardIndex));
  });
  return frame;
}

let FONT_FAMILY = "Noto Sans SC";

async function loadFonts() {
  const available = await figma.listAvailableFontsAsync();
  const hasNoto = available.some((font) => font.fontName.family === "Noto Sans SC" && font.fontName.style === "Regular");
  FONT_FAMILY = hasNoto ? "Noto Sans SC" : "Inter";
  const desired = ["Regular", "Medium", "Bold"];
  const supported = new Set(
    available
      .filter((font) => font.fontName.family === FONT_FAMILY)
      .map((font) => font.fontName.style),
  );
  const fallbackStyle = supported.has("Regular") ? "Regular" : [...supported][0];
  for (const style of desired) {
    if (!supported.has(style)) continue;
    await figma.loadFontAsync({ family: FONT_FAMILY, style });
  }
  if (!supported.has("Medium")) {
    await figma.loadFontAsync({ family: FONT_FAMILY, style: fallbackStyle });
  }
  if (!supported.has("Bold")) {
    await figma.loadFontAsync({ family: FONT_FAMILY, style: fallbackStyle });
  }
}

async function buildComponentsPage() {
  const page = figma.createPage();
  page.name = uniquePageName("组件");
  await figma.setCurrentPageAsync(page);

  const title = makeText("需求卡片组件", 24, "Bold", COLORS.text);
  title.x = 80;
  title.y = 64;
  page.appendChild(title);

  const variants = ["P0", "P1", "P2", "P3"].map(createCardComponent);
  variants.forEach((component, index) => {
    component.x = 80 + index * 285;
    component.y = 120;
  });
  const set = figma.combineAsVariants(variants, page);
  set.name = "Requirement Card";
  set.description = "需求卡片组件；四个优先级变体，包含需求ID、内容摘要、提交人头像与昵称。";
  set.x = 80;
  set.y = 120;
  set.layoutMode = "HORIZONTAL";
  set.itemSpacing = 40;
  set.paddingTop = 24;
  set.paddingRight = 24;
  set.paddingBottom = 24;
  set.paddingLeft = 24;
  set.primaryAxisSizingMode = "AUTO";
  set.counterAxisSizingMode = "AUTO";

  const map = {};
  set.children.forEach((component) => {
    const priority = component.name.split("=")[1];
    map[priority] = component;
  });
  return { page, componentSet: set, componentMap: map };
}

async function buildMainPage(componentMap) {
  const page = figma.createPage();
  page.name = uniquePageName("项目需求泳道");
  await figma.setCurrentPageAsync(page);
  page.backgrounds = [solid(COLORS.page)];

  const root = autoFrame("Desktop/Project Requirement Board", "VERTICAL", 1440, 900);
  root.x = 0;
  root.y = 0;
  root.clipsContent = true;
  setFill(root, COLORS.page);
  page.appendChild(root);

  const topbar = autoFrame("Top Navigation", "HORIZONTAL", 1440, 64);
  topbar.primaryAxisAlignItems = "SPACE_BETWEEN";
  topbar.counterAxisAlignItems = "CENTER";
  topbar.paddingLeft = 24;
  topbar.paddingRight = 24;
  setFill(topbar, COLORS.surface);
  setStroke(topbar, COLORS.border);
  topbar.appendChild(makeText("极简 AI 团队需求管理智能体", 20, "Bold", COLORS.text));
  const topActions = autoFrame("Top Actions", "HORIZONTAL", 240, 40);
  topActions.primaryAxisSizingMode = "AUTO";
  topActions.counterAxisSizingMode = "FIXED";
  topActions.counterAxisAlignItems = "CENTER";
  topActions.itemSpacing = 12;
  const role = autoFrame("Role/管理员", "HORIZONTAL", 96, 36);
  role.primaryAxisAlignItems = "CENTER";
  role.counterAxisAlignItems = "CENTER";
  role.cornerRadius = 6;
  setFill(role, COLORS.surface);
  setStroke(role, COLORS.blue);
  role.appendChild(makeText("需求管理员", 13, "Medium", COLORS.blue));
  topActions.appendChild(role);
  topActions.appendChild(makeButton("提交新需求", "primary"));
  topbar.appendChild(topActions);
  root.appendChild(topbar);

  const body = autoFrame("Workspace", "HORIZONTAL", 1440, 836);
  root.appendChild(body);

  const sidebar = autoFrame("Project Sidebar", "VERTICAL", 280, 836);
  sidebar.paddingTop = 24;
  sidebar.paddingRight = 16;
  sidebar.paddingBottom = 24;
  sidebar.paddingLeft = 16;
  sidebar.itemSpacing = 14;
  setFill(sidebar, COLORS.surface);
  setStroke(sidebar, COLORS.border);
  const sidebarHeader = autoFrame("Sidebar Header", "HORIZONTAL", 248, 36);
  sidebarHeader.primaryAxisAlignItems = "SPACE_BETWEEN";
  sidebarHeader.counterAxisAlignItems = "CENTER";
  sidebarHeader.appendChild(makeText("项目", 18, "Bold", COLORS.text));
  sidebarHeader.appendChild(makeButton("＋ 新建项目", "secondary"));
  sidebar.appendChild(sidebarHeader);
  PROJECTS.forEach(([name, count, selected]) => sidebar.appendChild(makeProjectGroup(name, count, selected)));
  body.appendChild(sidebar);

  const main = autoFrame("Main Content", "VERTICAL", 1160, 836);
  main.paddingTop = 24;
  main.paddingRight = 24;
  main.paddingBottom = 24;
  main.paddingLeft = 24;
  main.itemSpacing = 12;
  setFill(main, COLORS.page);

  const pageHeader = autoFrame("Page Header", "HORIZONTAL", 1112, 36);
  pageHeader.primaryAxisAlignItems = "SPACE_BETWEEN";
  pageHeader.counterAxisAlignItems = "CENTER";
  pageHeader.appendChild(makeText("智能客服平台  /  需求", 22, "Bold", COLORS.text));
  main.appendChild(pageHeader);

  const toolbar = autoFrame("Toolbar", "HORIZONTAL", 1112, 40);
  toolbar.primaryAxisAlignItems = "SPACE_BETWEEN";
  toolbar.counterAxisAlignItems = "CENTER";
  const toolbarLeft = autoFrame("Toolbar Filters", "HORIZONTAL", 470, 40);
  toolbarLeft.primaryAxisSizingMode = "AUTO";
  toolbarLeft.counterAxisSizingMode = "FIXED";
  toolbarLeft.itemSpacing = 12;
  toolbarLeft.appendChild(makeSearch(290));
  toolbarLeft.appendChild(makeSelect("全部优先级", 160));
  const toolbarRight = autoFrame("Toolbar Actions", "HORIZONTAL", 260, 40);
  toolbarRight.primaryAxisSizingMode = "AUTO";
  toolbarRight.counterAxisSizingMode = "FIXED";
  toolbarRight.itemSpacing = 12;
  toolbarRight.appendChild(makeButton("AI批量分析", "secondary"));
  toolbarRight.appendChild(makeButton("提交新需求", "primary"));
  toolbar.appendChild(toolbarLeft);
  toolbar.appendChild(toolbarRight);
  main.appendChild(toolbar);

  const sortNote = makeText("泳道内按优先级排序", 12, "Regular", COLORS.textMuted);
  sortNote.name = "Sort Rule";
  main.appendChild(sortNote);

  const board = autoFrame("Requirement Swimlanes", "HORIZONTAL", 1112, 648);
  board.itemSpacing = 12;
  LANES.forEach((lane, index) => board.appendChild(makeLane(lane, componentMap, index)));
  main.appendChild(board);
  body.appendChild(main);

  figma.currentPage.selection = [root];
  figma.viewport.scrollAndZoomIntoView([root]);
  return { page, root };
}

async function main() {
  await loadFonts();
  const { componentMap } = await buildComponentsPage();
  const { root } = await buildMainPage(componentMap);
  figma.currentPage.selection = [root];
  figma.viewport.scrollAndZoomIntoView([root]);
  figma.notify("项目需求泳道原型已生成");
  figma.closePlugin();
}

main().catch((error) => {
  figma.closePlugin(`生成失败：${error.message || String(error)}`);
});
