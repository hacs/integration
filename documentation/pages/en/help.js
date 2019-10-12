/**
 * Copyright (c) 2017-present, Facebook, Inc.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

const React = require('react');

const CompLibrary = require('../../core/CompLibrary.js');

const Container = CompLibrary.Container;
const GridBlock = CompLibrary.GridBlock;

function Help(props) {
  const { config: siteConfig, language = '' } = props;
  const { baseUrl, docsUrl } = siteConfig;
  const docsPart = `${docsUrl ? `${docsUrl}/` : ''}`;
  const langPart = `${language ? `${language}/` : ''}`;
  const docUrl = doc => `${baseUrl}${docsPart}${langPart}${doc}`;

  const supportLinks = [
    {
      content: `Learn more using the [documentation on this site.](${baseUrl})`,
      title: 'Browse Docs',
    },
    {
      content: '[Ask questions about the documentation and project.](https://community.home-assistant.io/t/custom-component-hacs/121727)',
      title: 'Join the community',
    },
    {
      content: "Find out what's new with this project over at [GitHub.](https://github.com/custom-components/hacs)",
      title: 'Stay up to date',
    },
    {
      content: `Need to submitt a bug? [Before you do make sure you first have a look here.](${docUrl('issues.html')})`,
      title: 'Submitt issues',
    },
    {
      content: `Want to submit a Feature request? [Before you do make sure you first have a look here.](${docUrl('issues.html')})`,
      title: 'Add feature requests'
    },
  ];

  return (
    <div className="docMainWrapper wrapper">
      <Container className="mainContainer documentContainer postContainer">
        <div className="post">
          <header className="postHeader">
            <h1>Need help?</h1>
          </header>
          <GridBlock contents={supportLinks} layout="threeColumn" />
        </div>
      </Container>
    </div>
  );
}

module.exports = Help;
