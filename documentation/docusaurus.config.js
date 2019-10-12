/**
 * Copyright (c) 2017-present, Facebook, Inc.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

module.exports = {
  title: 'HACS',
  tagline: 'Home Assistant Community Store',
  url: 'https://hacs.netlify.com',
  baseUrl: '/',
  favicon: 'img/favicon.ico',
  organizationName: 'custom-components',
  projectName: 'hacs',
  themeConfig: {
    navbar: {
      title: 'HACS',
      links: [
        { to: 'docs/installation/prerequisittes', label: 'Installation', position: 'left' },
        { to: 'docs/configuration/start', label: 'Configuration', position: 'left' },
        { to: 'docs/basic/getting_started', label: 'Usage', position: 'left' },
        { to: 'docs/developer/start', label: 'Developer docs', position: 'right' },
        { to: 'help', label: 'Help', position: 'right' },
        {
          href: 'https://github.com/custom-components/hacs',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
  },
  presets: [
    [
      '@docusaurus/preset-classic',
      {
        docs: {
          editUrl: 'https://github.com/custom-components/hacs/edit/master/documentation/content/',
          path: './content',
          sidebarPath: require.resolve('./sidebars.js'),
          showLastUpdateTime: true,
        },
        theme: {
          customCss: require.resolve('./src/css/custom.css'),
        },
      },
    ],
  ],
};
