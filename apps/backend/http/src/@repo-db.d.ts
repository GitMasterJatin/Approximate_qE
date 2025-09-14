declare module "@repo/db" {
  import { PrismaClient } from "@prisma/client";
  const prismaClient: PrismaClient;
  export default prismaClient;
}
