import std.stdio, std.random;


bool Clouds() {
	return uniform01 < 0.25;
}

bool Rain(bool clouds) {
	if (clouds) return uniform01 < 0.9;
	return uniform01 < 0.6;
}

bool Sprinkler(bool rain) {
	if (rain) return uniform01 < 0.12;
	return uniform01 < 0.45;
}

bool Wet(bool rain, bool sprinkler) {
	if (!rain && !sprinkler) return uniform01 < 0.0;
	if (!rain && sprinkler) return uniform01 < 0.79;
	if (rain && !sprinkler) return uniform01 < 0.82;
	if (rain && sprinkler) return uniform01 < 0.98;
	assert(0);
}

void main() {
	uint N = 10_000_000;

	uint count = 0;
	foreach (idx; 0..N) {
		auto clouds = Clouds();
		auto rain = Rain(clouds);
		auto sprinkler = Sprinkler(rain);
		auto wet = Wet(rain, sprinkler);
		count += wet;
	}

	writef("%.8f\n", count / cast(double)N);
}
