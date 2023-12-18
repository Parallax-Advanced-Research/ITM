import std.csv, std.stdio, std.algorithm, std.zlib, std.concurrency, std.utf,
	std.string, std.range, std.conv, std.path;

// yields one line at a time. Doesn't include the '\n'
// return value uses an internal buffer. Make a copy if you want it
// to stick around after the next iteration.
auto decompress_by_line(string path, uint chunk_size = 4096) {
	return new Generator!(char[])({
		auto decmp = new UnCompress;
		ubyte[] buf;
		buf.length = 4096;
		ulong offset = 0;//search for \n starting here
		ulong len = 0;//only buf[0..len] is valid
		ptrdiff_t found;

		auto result() {
			char[] r = buf[0..found].assumeUTF;
			std.utf.validate(r);
			return r;
		}

		auto pipeline = path
			.File("rb")
			.byChunk(chunk_size)
			.map!(a => cast(ubyte[])decmp.uncompress(a));

		foreach (chunk; pipeline) {
			// append chunk to buffer
			auto need = len + chunk.length;
			if (buf.length < need) buf.length = need;
			buf[len..len + chunk.length] = chunk[];
			len += chunk.length;

			// yield next line once we find a '\n', then remove returned bit from buffer
			found = offset + buf[offset..$].countUntil('\n');
			if (-1 != found) {
				yield(result);

				auto keep = buf[found+1..len];
				len = keep.length;
				copy(keep, buf[0..len]);//n.b. `the buf[0..len] = keep` syntax doesn't permit overlapping copies
				offset = 0;
			}
		}
		if (0 != len) {//permit last line to be terminated by EOF instead of '\n'
			yield(result);
		}
	});
}

void print_headers(string path) {
	writef("%20s : ", path.baseName);
	path.decompress_by_line
		.take(2)
		.joiner("\n")
		.csvReader!(string[string])(null)
		.front
		.keys
		.writeln
	;
}

void main(string[] argv) {
	// The original zip file needs to be extracted first; zip library is for the non-extended zip format, which doesn't support files over 4GB.
	//writef("%s\n", argv[1..$]);
	foreach (path; argv[1..$]) {
		print_headers(path);
	}
}

