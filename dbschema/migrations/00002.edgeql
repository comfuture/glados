CREATE MIGRATION m1ajib4jajg2zsxnjjtkryonggcul5i5pjvphso4l7bxtpzxbo3mlq
    ONTO m1rp6dvbqzldokj2u3cf7wc62yvva6dq54naxsyw3gu6dtsgd2tp4q
{
  CREATE TYPE default::Message {
      CREATE REQUIRED PROPERTY content: std::str;
      CREATE REQUIRED PROPERTY role: std::str {
          CREATE CONSTRAINT std::one_of('user', 'assistant', 'system');
      };
  };
  CREATE TYPE default::Session {
      CREATE MULTI LINK messages: default::Message {
          ON SOURCE DELETE DELETE TARGET IF ORPHAN;
          CREATE CONSTRAINT std::exclusive;
      };
      CREATE REQUIRED PROPERTY name: std::str;
  };
};
