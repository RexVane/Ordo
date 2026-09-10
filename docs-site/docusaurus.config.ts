import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Ordo Docs',
  tagline: '可控、可观测、可回归的企业知识能力层',
  favicon: 'img/favicon.ico',

  url: 'https://example.com',
  baseUrl: '/handbook/',

  organizationName: 'OWNER',
  projectName: 'Ordo',

  trailingSlash: false,

  staticDirectories: ['static', '../docs/images'],

  onBrokenLinks: 'throw',

  i18n: {
    defaultLocale: 'zh-Hans',
    locales: ['zh-Hans', 'en'],
    localeConfigs: {
      'zh-Hans': {
        label: '简体中文',
        htmlLang: 'zh-Hans',
        direction: 'ltr',
      },
      en: {
        label: 'English',
        htmlLang: 'en',
        direction: 'ltr',
      },
    },
  },

  themes: ['@docusaurus/theme-mermaid'],

  markdown: {
    mermaid: true,
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  presets: [
    [
      'classic',
      {
        docs: {
          path: 'docs',
          routeBasePath: 'docs',
          sidebarPath: './sidebars.ts',
          editUrl: 'https://example.com/OWNER/REPO/tree/main/docs-site/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/docusaurus-social-card.jpg',
    navbar: {
      title: 'Ordo',
      logo: {
        alt: 'Ordo',
        src: 'img/ordo-logo-image2-badge.png',
      },
      items: [
        {
          to: '/docs/ops/getting-started',
          position: 'left',
          label: '快速开始',
          activeBaseRegex: '^/docs/ops/getting-started',
        },
        {
          type: 'docSidebar',
          sidebarId: 'guide',
          position: 'left',
          label: '使用指南',
        },
        {
          type: 'dropdown',
          position: 'left',
          label: '开发者资源',
          items: [
            {to: '/docs/backend/welcome', label: '后端契约'},
            {to: '/docs/frontend/welcome', label: '前端路由'},
            {to: '/docs/integration/welcome', label: '集成与联调'},
          ],
        },
        {
          to: '/docs/ops/welcome',
          position: 'left',
          label: '运维',
          activeBaseRegex: '^/docs/ops/(?!getting-started)',
        },
        {
          type: 'localeDropdown',
          position: 'right',
        },
        {
          href: 'https://example.com/handbook/',
          label: 'API',
          position: 'right',
        },
        {
          href: 'https://example.com/OWNER/REPO',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    colorMode: {
      defaultMode: 'light',
      disableSwitch: false,
      respectPrefersColorScheme: false,
    },
    footer: {
      style: 'light',
      copyright: `© ${new Date().getFullYear()} Ordo · 可控、可观测、可回归`,
    },
    tableOfContents: {
      minHeadingLevel: 2,
      maxHeadingLevel: 3,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
