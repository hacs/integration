/**
 * Copyright (c) 2017-present, Facebook, Inc.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

// See https://docusaurus.io/docs/site-config for all the possible

const siteConfig = {
  title: 'HACS (Home Assistant Community Store)', // Title for your website.
  tagline: 'Home Assistant Community Store',
  url: 'https://hacs.netlify.com', // Your website URL
  baseUrl: '/', // Base URL for your project */
  projectName: 'hacs',
  organizationName: 'custom-components',
  editUrl: 'https://github.com/custom-components/hacs/edit/master/docs/',
  headerLinks: [
    { doc: 'developer/start', label: 'Developer docs' },
    { page: 'help', label: 'Help' },
    { href: 'https://github.com/custom-components/hacs', label: 'GitHub' },
  ],
  colors: {
    primaryColor: '#03a9f4',
    secondaryColor: '#424141',
  },
  highlight: {
    theme: 'default',
  },
  scripts: ['https://buttons.github.io/buttons.js'],

  onPageNav: 'separate',
  cleanUrl: true,
  repoUrl: 'https://github.com/custom-components/hacs',
};

module.exports = siteConfig;
