/**
 * Copyright (c) 2017-present, Facebook, Inc.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

module.exports = {
  title: 'HACS',
  tagline: 'Home Assistant Community Store',
  url: 'https://your-docusaurus-test-site.com',
  baseUrl: '/',
  favicon: 'img/favicon.ico',
  organizationName: 'custom-components', // Usually your GitHub org/user name.
  projectName: 'hacs', // Usually your repo name.
  themeConfig: {
    navbar: {
      title: 'HACS (Home Assistant Community Store)',
      links: [
        { to: 'docs/developer/start', label: 'Developer docs', position: 'right' },
        { to: 'help', label: 'Help', position: 'right' },
        {
          href: 'https://github.com/custom-components/hacs',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Getting started',
          items: [
            {
              label: 'Installation',
              to: 'docs/installation/manual',
            },
            {
              label: 'Configuration',
              to: 'docs/configuration/start',
            },
            {
              label: 'Usage',
              to: 'docs/basic/getting_started',
            },
          ],
        },
        {
          title: 'More Links',
          items: [
            {
              label: 'Community Forum',
              href: 'https://community.home-assistant.io/t/custom-component-hacs/121727',
            },
          ],
        },
      ],
    },
  },
  presets: [
    [
      '@docusaurus/preset-classic',
      {
        docs: {
          editUrl: 'https://github.com/custom-components/hacs/edit/master/documentation/docs/',
          path: './docs',
          sidebarPath: require.resolve('./sidebars.js'),
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      },
    ],
  ],
};
