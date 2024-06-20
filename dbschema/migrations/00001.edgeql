CREATE MIGRATION m1rp6dvbqzldokj2u3cf7wc62yvva6dq54naxsyw3gu6dtsgd2tp4q
    ONTO initial
{
  CREATE EXTENSION pgvector VERSION '0.4';
  CREATE SCALAR TYPE default::DocumentType EXTENDING enum<Document, Image, Video, Audio, File, Log>;
  CREATE SCALAR TYPE default::OpenAIEmbedding EXTENDING ext::pgvector::vector<1536>;
  CREATE TYPE default::Document {
      CREATE REQUIRED PROPERTY name: std::str;
      CREATE REQUIRED PROPERTY start_index: std::int16 {
          SET default := 0;
      };
      CREATE CONSTRAINT std::exclusive ON ((.name, .start_index));
      CREATE REQUIRED PROPERTY embedding: default::OpenAIEmbedding;
      CREATE INDEX ext::pgvector::ivfflat_cosine(lists := 3) ON (.embedding);
      CREATE REQUIRED PROPERTY content: std::str;
      CREATE REQUIRED PROPERTY type: default::DocumentType {
          SET default := (default::DocumentType.Document);
      };
  };
};
