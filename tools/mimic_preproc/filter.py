# Creates filtered versions of all the MIMIC-IV csv files that only include admissions that are potentially for injury
# (favors including false positives over filtering out false negatives)

import csv, os, sys

# If a given table only has one of these, we accept the rows that match that field. If it has both, it must match both.
# TODO: hadm_id -> subject_id should be many to one, no?
Hospital_Admission = str
Subject = str
OUTPUT_SUBDIR = 'trauma_only'

def get_csv_headers(path: str) -> list[str]:
	with open(path, newline='', encoding='utf-8') as fin:
		for row in csv.reader(fin):
			return row

	assert False, f"{path} is empty"

def filter_mimic(dirname: str) -> None:
	os.chdir(dirname)
	paths = [ path for path in os.listdir(dirname) if '.csv' == os.path.splitext(path)[1] ]
	headers: dict[str, list[str]] = {}
	for path in paths:
		if '.csv' != os.path.splitext(path)[1]: continue
		headers[path] = get_csv_headers(path)
						
	trauma_admissions = get_trauma_admissions(paths, headers)
	trauma_subjects = set(trauma_admissions.values())

	print("\x1b[94mFiltering files:\x1b[0m")

	assert not os.path.exists(OUTPUT_SUBDIR) or os.isdir(OUTPUT_SUBDIR),\
		f"{OUTPUT_SUBDIR} exists, but is not a directory"	
	os.mkdir(OUTPUT_SUBDIR)

	for path in paths:
		print(path)
		output_path = os.path.join(OUTPUT_SUBDIR, path)
		assert not os.path.exists(output_path), f"{output_path} already exists"
		with open(output_path, 'w', encoding='utf-8') as fout, open(path, 'r', encoding='utf-8') as fin:
			writer = csv.writer(fout)
			hadm_idx = headers[path].index('hadm_id') if 'hadm_id' in headers[path]  else None
			subject_idx = headers[path].index('subject_id') if 'subject_id' in headers[path]  else None
			include_all = False
			if hadm_idx is None and subject_idx is None:
				print(f"{path} doesn't have hadm_id or subject_id fields: including all rows")
				# TODO: Could make it a symlink, but then it probably doesn't work on windows
				include_all = True

			def valid_row(hadm: str | None, subject: str | None) -> bool:
				if hadm is None:  return subject in trauma_subjects
				if hadm not in trauma_admissions:  return False

				assert subject is None or trauma_admissions[hadm] == subject,\
					"{path}: Subject ({subject}) doesn't match the one expected for hadm_id {hadm}"
				return True

			for idx, row in enumerate(csv.reader(fin)):
				hadm = None if hadm_idx is None else row[hadm_idx]
				subject = None if subject_idx is None else row[subject_idx]
				if include_all or 0 == idx or valid_row(hadm, subject):
					writer.writerow(row)


def get_trauma_admissions(paths: list[str], headers: dict[str, list[str]]) -> dict[Hospital_Admission, Subject]:
	""" Get a list of all `subject_id,hadm_id`s that correspond to an `icd_code` in the "injury" category. Error on the side of including """

	def remove_foofix(s: str, foofixes: list[str]) -> str:
		""" Each entry of foofixes should be a single character. It will be removed if it's a prefix or suffix. """
		for idx,_ in enumerate(foofixes): # if foofixes = [ V,Z ], and s is "ZV000", we need a second pass to catch the V.
			for foofix in foofixes[idx:]:
				if foofix == s[0]: s = s[1:]
				if foofix == s[-1]: s = s[:-1]
		return s
	
	valid_entries: dict[Hospital_Admission, Subject] = {}
	print("\x1b[94mReading (subject_id, hadm_id, icd_code) tuples found from:\x1b[0m")
	n_valid_codes = 0
	n_trauma_codes = 0
	n_bogus_codes = 0

	def trauma_code(icd_version: str, icd_code: str) -> bool | None:
		""" Returns true if it's a trauma code, false if it isn't, and None if we can't parse it """
		if '9' == icd_version:
			icd_code = remove_foofix(icd_code, ['V','Z'])
			if 'E' == icd_code[0]:
				# describes type of event rather than type of injury. 
				# A few ranges are specifically military or war related, but I'm including all.
				# Also, the ones that are more than 4 characters are probably really something like E000.42, so I should only filter by the first 4.
				return True 
			try:
				icd = int(icd_code)
				return 800 <= icd <= 999
			except:
				#sys.stderr.write(f"BOGUS: ICD-{icd_version}: {icd_code}\n")
				return None
		if '10' == icd_version:
			if len(icd_code) < 3 or not icd_code[0].isalpha() or not icd_code[1].isdigit() or not icd_code[2].isdigit():
				#if len(icd_code) < 3:
				#	sys.stderr.write(f"BOGUS: ICD-{icd_version}: {icd_code}\n")
				#else:
				#	sys.stderr.write(f"BOGUS: ICD-{icd_version}: {icd_code} ({icd_code[0].isalpha()}, {icd_code[1].isdigit()}, {icd_code[2].isdigit()})\n")
				return None
			else:
				letter = icd_version[0].upper()
				n = int(icd_version[1:2])
				return 'S' == letter or ('T' == letter and 7 <= n <= 88) # Weird: The rest of T doesn't seem to be used.

		assert False, f"Unrecognized icd_version: {icd_version}"

	for path in paths:
		if 'subject_id' in headers[path] and 'icd_code' in headers[path]:
			print(path)
			with open(path, newline='', encoding='utf-8') as fin:
				for idx, row in enumerate(csv.reader(fin)):
					#print(row)
					if 0 == idx:
						subject_id_idx = row.index('subject_id')
						hadm_id_idx = row.index('hadm_id')
						icd_code_idx = row.index('icd_code')
						icd_version_idx = row.index('icd_version')
					else:
						icd_trauma = trauma_code(row[icd_version_idx], row[icd_code_idx])
						if icd_trauma is None:
							n_bogus_codes += 1 # TODO: handle these
						elif icd_trauma:
							n_trauma_codes += 1
							adm = row[hadm_id_idx]
							subj = row[subject_id_idx]
							assert adm not in valid_entries or subj == valid_entries[adm], "Multiple patients for same hospital stay. We assume that can't happen"
							valid_entries[row[hadm_id_idx]] = row[subject_id_idx]
						n_valid_codes += 1

	print(f"Found {n_trauma_codes} trauma entries ({len(valid_entries)} hospital admissions) of {n_valid_codes} total recognized entries (rejected {n_bogus_codes} rows due to unrecognized codes)")
	print()

	return valid_entries

filter_mimic(sys.argv[1])
