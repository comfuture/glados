using extension pgvector;

module default {
  scalar type OpenAIEmbedding extending ext::pgvector::vector<1536>;
  scalar type DocumentType extending enum<Document, Image, Video, Audio, File, Log>;

  type Document {
    required type: DocumentType {
      default := DocumentType.Document;
    }
    required name: str;
    required start_index: int16 {
      default := 0;
    }
    required content: str;
    required embedding: OpenAIEmbedding;

    constraint exclusive on ((.name, .start_index));
    index ext::pgvector::ivfflat_cosine(lists := 3) on (.embedding);
  }

  type Session {
    required name: str;
    multi messages: Message {
      constraint exclusive;
      on source delete delete target if orphan;
    }
  }

  type Message {
    required role: str {
      constraint one_of("user", "assistant", "system");
    }
    required content: str;
  }
}
