echo off
SET "MFM_HDDdataOneSector=_erase_"
SET "test=_erase_"

REM generate reference file and CRC
IF "%1"=="-r" (
	ECHO generate reference MFM_HDDdataOneSector.7z file
	"C:\Program Files\sigrok\sigrok-cli\sigrok-cli" -D -i ..\test\MFM_HDDdataOneSector.sr -P mfm:dsply_pfx=yes:dsply_sn=yes | "C:\Program Files\7-Zip\7z" a -si MFM_HDDdataOneSector.7z

    ECHO generating reference MFM_HDDdataOneSector.crc
	"C:\Program Files\7-Zip\7z" l -slt MFM_HDDdataOneSector.7z |findstr /b CRC |for /f "tokens=3 delims= " %%i in ('more') do @echo %%i > MFM_HDDdataOneSector.crc
)

REM read reference MFM_HDDdataOneSector.crc
set /p MFM_HDDdataOneSector=<MFM_HDDdataOneSector.crc
set MFM_HDDdataOneSector=%MFM_HDDdataOneSector: =%

REM generate test.crc
"C:\Program Files\sigrok\sigrok-cli\sigrok-cli" -D -i ..\test\MFM_HDDdataOneSector.sr -P mfm:dsply_pfx=yes:dsply_sn=yes |"C:\Program Files\7-Zip\7z" h -si |findstr data |for /f "tokens=4 delims= " %%G in ('more') do @echo %%G> test.crc
set /p test=<test.crc
set test=%test: =%
del test.crc

IF "%MFM_HDDdataOneSector%"=="%test%" (
    echo OK %MFM_HDDdataOneSector% = %test%
) ELSE (
    echo %MFM_HDDdataOneSector% != %test% ERROR && pause
)

REM Sanity check, try comparing to different annotations output (mfm=mrk means only IDAM/DAM output)
"C:\Program Files\sigrok\sigrok-cli\sigrok-cli" -D -i ..\test\MFM_HDDdataOneSector.sr -P mfm:dsply_pfx=yes:dsply_sn=yes -A mfm=mrk|"C:\Program Files\7-Zip\7z" h -si |findstr data |for /f "tokens=4 delims= " %%G in ('more') do @echo %%G> test.crc
set /p test=<test.crc
set test=%test: =%

IF "%MFM_HDDdataOneSector%"=="%test%" (
    echo Sanity check FAILED && pause
) ELSE (
    echo OK %MFM_HDDdataOneSector% != %test%
)