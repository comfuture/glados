import * as edgedb from "edgedb";

export function useEdgeDB() {
  const client = edgedb.createClient({
    instanceName: "comfuture/edgedb",
    database: process.env.EDGEDB_DATABASE,
    user: "edgedb",
    password: process.env.EDGEDB_SECRET_KEY    
  });
  return client;
}
