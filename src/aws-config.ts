import { Amplify } from 'aws-amplify';

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: 'eu-central-1_9rFrWwPhk',
      userPoolClientId: '6ugjmblqmjv7eq61bgolfa2pil',
      loginWith: {
        username: true,
      },
    }
  }
});
