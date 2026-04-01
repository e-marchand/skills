//%attributes = {"invisible":true}
var $startUpParams : Text
var $r:=Get database parameter(User param value; $startUpParams)

// parse optional page number from separator ":"  (e.g. "MyForm:2")
var $formName : Text
var $pageNumber : Integer:=-1
var $sepPos:=Position(":"; $startUpParams)
If ($sepPos>0)
	$formName:=Substring($startUpParams; 1; $sepPos-1)
	$pageNumber:=Num(Substring($startUpParams; $sepPos+1))
	If ($pageNumber<1)
		$pageNumber:=-1
	End if 
Else 
	$formName:=$startUpParams
End if 

// if file get form for name
If (Position("/"; $formName)>0)
	If (Position("form.4DForm"; $formName)>0)
		If (Position("Project/"; $formName)=1)
			$formName:=Try(Folder(fk database folder).file($formName).parent.name)
		Else 
			$formName:=Try(File($formName; fk posix path).parent.name)
		End if 
	End if 
End if 

// take the screenshot
var $screenshot : Picture
If ($pageNumber>=0)
	FORM SCREENSHOT($formName; $screenshot; $pageNumber)
Else 
	FORM SCREENSHOT($formName; $screenshot)
End if 
var $blob : Blob
PICTURE TO BLOB($screenshot; $blob; ".png")

// save the screenshot and log
var $formFolder:=Folder(fk database folder).folder("Project/Sources/Forms/"+$formName)
var $f:=$formFolder.file("form.png")
$f.setContent($blob)
LOG EVENT(Into system standard outputs; $f.path; Information message)

QUIT 4D