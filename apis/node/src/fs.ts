import fs from "fs/promises";
import zlib from "zlib";
import path from "path";
import mime from "mime-types";
import type { AxiosResponse, AxiosRequestHeaders } from "axios";
import type { ClientInterface } from "./types";
import { fileImageFills, fileImages } from "./fmt";

const _mock_axios_request = async <T = any>(
  path: string
): Promise<AxiosResponse<T>> => {
  try {
    const { size: content_length } = await fs.stat(path);
    const content_type = mime.lookup(path) || "application/json";
    const buffer = await fs.readFile(path);
    const txt = (
      path.endsWith(".gz") ? await zlib.gunzipSync(buffer) : buffer
    ).toString();
    const data = JSON.parse(txt) as T;
    return {
      data: data as T,
      status: 200,
      statusText: "OK",
      headers: {},
      config: {
        headers: {
          Accept: content_type,
          "Content-Length": content_length,
          "User-Agent": "@figma-api/community/fs",
          "Content-Encoding": path.endsWith(".gz") ? "gzip" : "utf-8",
          "Content-Type": "application/json",
        } as AxiosRequestHeaders,
      },
    };
  } catch (e) {
    return {
      data: null as any,
      status: 404,
      statusText: "Not Found",
      headers: {},
      config: {
        headers: {} as AxiosRequestHeaders,
      },
    };
  }
};

export const Client = ({
  paths,
}: {
  paths: {
    files: string;
    images: string;
  };
}): ClientInterface => {
  const clients = {
    file: {
      get: async (url: string) =>
        _mock_axios_request(path.join(paths.files, url)),
    },
    image: {
      get: async (url: string) =>
        _mock_axios_request(path.join(paths.images, url)),
    },
  };

  return {
    meta: (fileId) => clients.file.get(`/${fileId}/meta.json`),
    file: (fileId, params = {}) =>
      // params not supported atm
      clients.file.get(`/${fileId}/file.json.gz`),

    // fileNodes: (fileId, params) =>
    //   clients.file.get(`files/${fileId}/nodes`, {
    //     params: {
    //       ...params,
    //       ids: params.ids.join(","),
    //     },
    //   }),

    fileImages: async (fileId, params) => {
      const res = await clients.image.get(`/${fileId}/exports/meta.json`);
      const { data } = res;

      return {
        ...res,
        data: fileImages(fileId, data, params, paths.images),
      };
    },

    fileImageFills: async (fileId) => {
      const res = await clients.image.get(`/${fileId}/images/meta.json`);
      const { data } = res;

      if (res.status === 200) {
        return {
          ...res,
          data: fileImageFills(fileId, data, paths.images),
        };
      } else {
        return res;
      }
    },
  };
};
