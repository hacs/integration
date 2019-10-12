const siteConfig = {

  tagline: 'Home Assistant Community Store',
  url: 'https://hacs.netlify.com', // Your website URL
  baseUrl: '/', // Base URL for your project */
  projectName: 'hacs',
  organizationName: 'custom-components',
  editUrl: 'https://github.com/custom-components/hacs/edit/master/docs/',
  headerLinks: [
    { to: 'developer/start', label: 'Developer docs', position: 'left' },
    { to: 'help', label: 'Help', position: 'left' },
    { href: 'https://github.com/custom-components/hacs', label: 'GitHub', position: 'left' },
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

//module.exports = siteConfig;

module.exports = {
  title: 'HACS (Home Assistant Community Store)', // Title for your website.
  baseUrl: '/', // Base URL for your project */
  url: 'https://hacs.netlify.com', // Your website URL
  tagline: 'Home Assistant Community Store',
  favicon: "",
  githubHost: 'github.com',
  organizationName: 'custom-components',
  themeConfig: {
    navbar: {
      title: 'HACS (Home Assistant Community Store)', // Title for your website.
      links: [
        { to: 'developer/start', label: 'Developer docs', position: 'left' },
        { to: 'help', label: 'Help', position: 'left' },
        { href: 'https://github.com/custom-components/hacs', label: 'GitHub', position: 'left' },
      ],
    },
    scripts: ['https://buttons.github.io/buttons.js'],
    presets: [
      [
        '@docusaurus/preset-classic',
        {
          docs: {
            editUrl: 'https://github.com/custom-components/hacs/edit/master/documentation/docs/',
            path: './docs',
            sidebarPath: require.resolve('./sidebars.json'),
          },

        },
      ],
    ],
  }
}