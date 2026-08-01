param(
    [Parameter(Mandatory = $true)]
    [string]$ArticleDir,

    [long]$AppHwnd = 70919330,

    [switch]$SaveDraft
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class WeChatTemplateInput {
    [DllImport("user32.dll")] public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr c);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint x, uint y, uint d, UIntPtr e);
    [DllImport("user32.dll")] public static extern void keybd_event(byte v, byte s, uint f, UIntPtr e);
}
'@

[WeChatTemplateInput]::SetThreadDpiAwarenessContext([IntPtr](-4)) | Out-Null

$sourcePath = Join-Path $ArticleDir "article_source.json"
if (-not (Test-Path -LiteralPath $sourcePath)) {
    throw "Missing article_source.json: $sourcePath"
}
$article = Get-Content -LiteralPath $sourcePath -Raw -Encoding utf8 | ConvertFrom-Json

$root = [System.Windows.Automation.AutomationElement]::FromHandle([IntPtr]$AppHwnd)
$all = $root.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants,
    [System.Windows.Automation.Condition]::TrueCondition
)
$editors = @()
foreach ($element in $all) {
    try {
        if ($element.Current.ClassName -eq "ProseMirror") {
            $rectangle = $element.Current.BoundingRectangle
            $editors += [pscustomobject]@{
                Element = $element
                Rectangle = $rectangle
            }
        }
    } catch {}
}

$bodyEditor = $editors | Sort-Object { $_.Rectangle.Height } -Descending | Select-Object -First 1
$titleEditor = $editors |
    Where-Object { $_.Rectangle.Height -lt 100 -and $_.Rectangle.Top -gt 450 } |
    Sort-Object { $_.Rectangle.Top } |
    Select-Object -First 1
if (-not $bodyEditor -or -not $titleEditor) {
    throw "Could not identify the title and body ProseMirror editors."
}

[WeChatTemplateInput]::keybd_event(0x12, 0, 0, [UIntPtr]::Zero)
[WeChatTemplateInput]::keybd_event(0x12, 0, 2, [UIntPtr]::Zero)
[WeChatTemplateInput]::SetForegroundWindow([IntPtr]$AppHwnd) | Out-Null

function Invoke-PhysicalClick {
    param(
        [double]$X,
        [double]$Y
    )
    [WeChatTemplateInput]::SetCursorPos([int]$X, [int]$Y) | Out-Null
    [WeChatTemplateInput]::mouse_event(2, 0, 0, 0, [UIntPtr]::Zero)
    [WeChatTemplateInput]::mouse_event(4, 0, 0, 0, [UIntPtr]::Zero)
    Start-Sleep -Milliseconds 300
}

function ConvertTo-CfHtml {
    param(
        [string]$Fragment,
        [string]$PlainText
    )
    $prefix = "<html><body><!--StartFragment-->"
    $suffix = "<!--EndFragment--></body></html>"
    $html = $prefix + $Fragment + $suffix
    $encoding = [System.Text.Encoding]::UTF8
    $newLine = [Environment]::NewLine
    $dummyHeader = "Version:1.0" + $newLine +
        "StartHTML:0000000000" + $newLine +
        "EndHTML:0000000000" + $newLine +
        "StartFragment:0000000000" + $newLine +
        "EndFragment:0000000000" + $newLine
    $startHtml = $encoding.GetByteCount($dummyHeader)
    $startFragment = $startHtml + $encoding.GetByteCount($prefix)
    $endFragment = $startFragment + $encoding.GetByteCount($Fragment)
    $endHtml = $startHtml + $encoding.GetByteCount($html)
    $header = "Version:1.0" + $newLine +
        ("StartHTML:{0:D10}" -f $startHtml) + $newLine +
        ("EndHTML:{0:D10}" -f $endHtml) + $newLine +
        ("StartFragment:{0:D10}" -f $startFragment) + $newLine +
        ("EndFragment:{0:D10}" -f $endFragment) + $newLine

    $dataObject = New-Object System.Windows.Forms.DataObject
    $dataObject.SetData([System.Windows.Forms.DataFormats]::Html, $header + $html)
    $dataObject.SetData([System.Windows.Forms.DataFormats]::UnicodeText, $PlainText)
    [System.Windows.Forms.Clipboard]::SetDataObject($dataObject, $true)
}

function ConvertTo-HtmlText {
    param([string]$Text)
    return [System.Net.WebUtility]::HtmlEncode($Text)
}

function Get-WeChatCharacterCount {
    param([string]$Text)
    $asciiCount = 0
    foreach ($character in $Text.ToCharArray()) {
        if ([int]$character -le 127) {
            $asciiCount++
        }
    }
    $nonAsciiCount = $Text.Length - $asciiCount
    return $nonAsciiCount + [Math]::Ceiling($asciiCount / 2.0)
}

function Get-WeChatRecommendation {
    param($Article)

    $englishTitle = [string]$Article.title_en
    $chineseTitle = [string]$Article.title_cn
    $full = "本期为大家推荐的内容为论文《$englishTitle》（$chineseTitle），发表在 Transactions in Urban Data, Science, and Technology 期刊，欢迎大家学习与交流。"
    if ((Get-WeChatCharacterCount $full) -le 120) {
        return $full
    }

    # Keep both verified titles intact. Compress only the boilerplate that
    # causes the platform recommendation to exceed its 120-character limit.
    $shortJournal = "本期为大家推荐的内容为论文《$englishTitle》（$chineseTitle），发表于TUS，欢迎大家学习与交流。"
    if ((Get-WeChatCharacterCount $shortJournal) -le 120) {
        return $shortJournal
    }

    $shortIntro = "本期推荐论文《$englishTitle》（$chineseTitle），发表于TUS，欢迎大家学习与交流。"
    if ((Get-WeChatCharacterCount $shortIntro) -le 120) {
        return $shortIntro
    }

    $compact = "本期推荐论文《$englishTitle》（$chineseTitle），发表于TUS，欢迎学习与交流。"
    if ((Get-WeChatCharacterCount $compact) -le 120) {
        return $compact
    }

    throw "The platform recommendation still exceeds 120 characters after minimal boilerplate compression."
}

function Get-ArticleCollectionArea {
    param(
        [System.Windows.Automation.AutomationElement]$AutomationRoot
    )

    $labelCondition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty,
        "合集"
    )
    $labels = $AutomationRoot.FindAll(
        [System.Windows.Automation.TreeScope]::Descendants,
        $labelCondition
    )
    $walker = [System.Windows.Automation.TreeWalker]::RawViewWalker
    foreach ($label in $labels) {
        $candidate = $label
        for ($level = 0; $level -lt 6 -and $candidate; $level++) {
            if ($candidate.Current.AutomationId -eq "js_article_tags_area") {
                return $candidate
            }
            $candidate = $walker.GetParent($candidate)
        }
    }
    return $null
}

# Set the headline before replacing the body because the body paste scrolls to its end.
$headline = "论文推荐 | " + [string]$article.title_cn
$titleRectangle = $titleEditor.Rectangle
Invoke-PhysicalClick -X ($titleRectangle.Left + 120) -Y ($titleRectangle.Top + 30)
[System.Windows.Forms.Clipboard]::SetText($headline)
[System.Windows.Forms.SendKeys]::SendWait("^a")
[System.Windows.Forms.SendKeys]::SendWait("^v")
Start-Sleep -Milliseconds 500

# Copy the complete rich-text template.
$bodyRectangle = $bodyEditor.Rectangle
Invoke-PhysicalClick -X ($bodyRectangle.Left + 100) -Y ($bodyRectangle.Top + 100)
[System.Windows.Forms.SendKeys]::SendWait("^a")
[System.Windows.Forms.SendKeys]::SendWait("^c")
Start-Sleep -Milliseconds 700

$plainTemplate = [System.Windows.Forms.Clipboard]::GetText()
$rawHtml = [string][System.Windows.Forms.Clipboard]::GetData(
    [System.Windows.Forms.DataFormats]::Html
)
$fragmentMatch = [regex]::Match(
    $rawHtml,
    "<!--StartFragment-->([\s\S]*?)<!--EndFragment-->"
)
if (-not $fragmentMatch.Success) {
    throw "The copied body did not contain a CF_HTML fragment."
}
$fragment = $fragmentMatch.Groups[1].Value

$oldEnglishTitle = "Nonlinear impacts of the configuration elements of life services on spatial vitality in the online-merge-offline context: A case study of Shanghai, China"
$oldChineseTitle = "生活服务配置要素对线上-线下融合情境下空间活力的非线性影响：以上海为例"
$oldAuthors = "Jing He, He Zhang*, Linghong Ke, Wenpei Zhou, Jingyi Peng"
$oldDoi = "https://doi.org/10.1177/27541231261426518"
$oldGuide = [regex]::Match(
    $plainTemplate,
    "随着线上-线下融合[\s\S]+?提供了参考。"
).Value.Trim()
$oldAbstract = [regex]::Match(
    $plainTemplate,
    "Despite the growing prevalence[\s\S]+?service configuration\."
).Value.Trim()
if (-not $oldGuide -or -not $oldAbstract) {
    throw "Could not identify the template guide or abstract."
}

$correspondingNames = @(
    $article.corresponding_authors | ForEach-Object { [string]$_.name }
)
$authorNames = @()
foreach ($author in $article.authors) {
    $name = [string]$author.name
    if ($correspondingNames -contains $name) {
        $name += "*"
    }
    $authorNames += $name
}
$authorLine = $authorNames -join ", "

$fragment = $fragment.Replace(
    $oldEnglishTitle,
    (ConvertTo-HtmlText ([string]$article.title_en))
)
$fragment = $fragment.Replace(
    $oldChineseTitle,
    (ConvertTo-HtmlText ([string]$article.title_cn))
)
$fragment = $fragment.Replace(
    $oldAuthors,
    (ConvertTo-HtmlText $authorLine)
)
$fragment = $fragment.Replace(
    $oldDoi,
    (ConvertTo-HtmlText ("https://doi.org/" + [string]$article.doi))
)
$fragment = $fragment.Replace(
    $oldGuide,
    (ConvertTo-HtmlText ([string]$article.guide_cn))
)
$fragment = $fragment.Replace(
    $oldAbstract,
    (ConvertTo-HtmlText ([string]$article.abstract_en))
)

$imageDataUrls = @()
foreach ($imageFile in $article.image_files) {
    $imagePath = Join-Path $ArticleDir $imageFile
    if (-not (Test-Path -LiteralPath $imagePath)) {
        throw "Missing paper image: $imagePath"
    }
    $imageDataUrls += "data:image/jpeg;base64," +
        [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($imagePath))
}
if ($imageDataUrls.Count -ne 5) {
    throw "Expected exactly five paper images, got $($imageDataUrls.Count)."
}

# The template has four centered paper-page wrappers. Replace those and clone
# the last wrapper once so the resulting article has five paper pages.
$paperWrapperPattern = '<section style="text-align: center;" nodeleaf="">\s*<img\b[^>]*>\s*</section>'
$script:paperWrapperIndex = 0
$fragment = [regex]::Replace(
    $fragment,
    $paperWrapperPattern,
    {
        param($match)
        $script:paperWrapperIndex++
        $index = $script:paperWrapperIndex - 1
        $wrapper = [regex]::Replace(
            $match.Value,
            '(\bsrc=")[^"]*(")',
            ('$1' + $imageDataUrls[$index] + '$2'),
            1
        )
        if ($script:paperWrapperIndex -eq 4) {
            $fifthWrapper = [regex]::Replace(
                $match.Value,
                '(\bsrc=")[^"]*(")',
                ('$1' + $imageDataUrls[4] + '$2'),
                1
            )
            return $wrapper + $fifthWrapper
        }
        return $wrapper
    }
)
if ($script:paperWrapperIndex -ne 4) {
    throw "Expected four paper-image wrappers in the template, got $script:paperWrapperIndex."
}

ConvertTo-CfHtml -Fragment $fragment -PlainText ([string]$article.guide_cn)
[System.Windows.Forms.SendKeys]::SendWait("^a")
[System.Windows.Forms.SendKeys]::SendWait("^v")
Start-Sleep -Seconds 12

# The paste leaves body focus active, so copying here provides a reliable,
# lossless pre-save validation of text and images.
[System.Windows.Forms.SendKeys]::SendWait("^a")
[System.Windows.Forms.SendKeys]::SendWait("^c")
Start-Sleep -Milliseconds 700
$validatedPlain = [System.Windows.Forms.Clipboard]::GetText()
$validatedHtml = [string][System.Windows.Forms.Clipboard]::GetData(
    [System.Windows.Forms.DataFormats]::Html
)
$imageCount = [regex]::Matches($validatedHtml, "<img\b").Count
$checks = [ordered]@{
    EnglishTitle = $validatedPlain.Contains([string]$article.title_en)
    ChineseTitle = $validatedPlain.Contains([string]$article.title_cn)
    DOI = $validatedPlain.Contains([string]$article.doi)
    Authors = $validatedPlain.Contains($authorLine)
    Guide = $validatedPlain.Contains(([string]$article.guide_cn).Substring(0, 30))
    Abstract = $validatedPlain.Contains(([string]$article.abstract_en).Substring(0, 50))
    OldTitleRemoved = -not $validatedPlain.Contains($oldChineseTitle)
    Images = $imageCount
}
$booleanChecks = @(
    $checks.EnglishTitle,
    $checks.ChineseTitle,
    $checks.DOI,
    $checks.Authors,
    $checks.Guide,
    $checks.Abstract,
    $checks.OldTitleRemoved
)
if ($booleanChecks -contains $false -or $imageCount -ne 10) {
    throw "Pre-save validation failed: $($checks | ConvertTo-Json -Compress)"
}

# The platform recommendation reuses the article lead sentence. The verified
# English and Chinese titles are preserved; boilerplate is shortened only when
# WeChat's weighted counter would otherwise exceed 120 characters.
$recommendation = Get-WeChatRecommendation $article
$recommendationCount = Get-WeChatCharacterCount $recommendation
$descriptionCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::AutomationIdProperty,
    "js_description"
)
$descriptionEditor = $root.FindFirst(
    [System.Windows.Automation.TreeScope]::Descendants,
    $descriptionCondition
)
if (-not $descriptionEditor) {
    throw "The platform recommendation field was not found."
}
$descriptionEditor.GetCurrentPattern(
    [System.Windows.Automation.ScrollItemPattern]::Pattern
).ScrollIntoView()
Start-Sleep -Milliseconds 400
$descriptionRectangle = $descriptionEditor.Current.BoundingRectangle
Invoke-PhysicalClick `
    -X ($descriptionRectangle.Left + ($descriptionRectangle.Width / 2)) `
    -Y ($descriptionRectangle.Top + ($descriptionRectangle.Height / 2))
[System.Windows.Forms.Clipboard]::SetText($recommendation)
[System.Windows.Forms.SendKeys]::SendWait("^a")
[System.Windows.Forms.SendKeys]::SendWait("^v")
Start-Sleep -Milliseconds 500

# "原文链接" is independent of DOI text inside the article body. Open its
# popover and set the paper-specific DOI URL explicitly.
$doiUrl = "https://doi.org/" + [string]$article.doi
$urlAreaCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::AutomationIdProperty,
    "js_article_url_area"
)
$urlArea = $root.FindFirst(
    [System.Windows.Automation.TreeScope]::Descendants,
    $urlAreaCondition
)
if (-not $urlArea) {
    throw "The original-link setting was not found."
}
$urlArea.GetCurrentPattern(
    [System.Windows.Automation.ScrollItemPattern]::Pattern
).ScrollIntoView()
Start-Sleep -Milliseconds 400
$textCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Text
)
$urlTexts = $urlArea.FindAll(
    [System.Windows.Automation.TreeScope]::Descendants,
    $textCondition
)
$currentUrlElement = $null
foreach ($urlText in $urlTexts) {
    if ($urlText.Current.Name -match '^https://doi\.org/') {
        $currentUrlElement = $urlText
        break
    }
}
if (-not $currentUrlElement) {
    throw "The current original-link value was not found."
}
$urlRectangle = $currentUrlElement.Current.BoundingRectangle
Invoke-PhysicalClick `
    -X ($urlRectangle.Left + ($urlRectangle.Width / 2)) `
    -Y ($urlRectangle.Top + ($urlRectangle.Height / 2))
$urlInputCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::NameProperty,
    "输入或粘贴原文链接"
)
$urlInput = $root.FindFirst(
    [System.Windows.Automation.TreeScope]::Descendants,
    $urlInputCondition
)
if (-not $urlInput) {
    throw "The original-link popover did not open."
}
$urlInputRectangle = $urlInput.Current.BoundingRectangle
Invoke-PhysicalClick `
    -X ($urlInputRectangle.Left + ($urlInputRectangle.Width / 2)) `
    -Y ($urlInputRectangle.Top + ($urlInputRectangle.Height / 2))
[System.Windows.Forms.Clipboard]::SetText($doiUrl)
[System.Windows.Forms.SendKeys]::SendWait("^a")
[System.Windows.Forms.SendKeys]::SendWait("^v")
Start-Sleep -Milliseconds 300
$confirmCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::NameProperty,
    "确定"
)
$confirmButton = $root.FindFirst(
    [System.Windows.Automation.TreeScope]::Descendants,
    $confirmCondition
)
if (-not $confirmButton) {
    throw "The original-link confirmation button was not found."
}
$confirmButton.GetCurrentPattern(
    [System.Windows.Automation.InvokePattern]::Pattern
).Invoke()
Start-Sleep -Milliseconds 700
$doiCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::NameProperty,
    $doiUrl
)
$savedUrlElement = $root.FindFirst(
    [System.Windows.Automation.TreeScope]::Descendants,
    $doiCondition
)
if (-not $savedUrlElement) {
    throw "Original-link validation failed: expected $doiUrl"
}

# This script is exclusively for the 论文推荐 workflow. Assign those articles
# to the 论文推荐 collection; other WeChat content types must not inherit this
# rule merely because they use the same account.
$collectionName = "论文推荐"
$collectionArea = Get-ArticleCollectionArea -AutomationRoot $root
if (-not $collectionArea) {
    throw "The article collection setting was not found."
}
$collectionArea.GetCurrentPattern(
    [System.Windows.Automation.ScrollItemPattern]::Pattern
).ScrollIntoView()
Start-Sleep -Milliseconds 400
$collectionCondition = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::NameProperty,
    $collectionName
)
$selectedCollection = $collectionArea.FindFirst(
    [System.Windows.Automation.TreeScope]::Descendants,
    $collectionCondition
)
if (-not $selectedCollection) {
    $unassignedCondition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty,
        "未添加"
    )
    $unassignedElement = $collectionArea.FindFirst(
        [System.Windows.Automation.TreeScope]::Descendants,
        $unassignedCondition
    )
    if (-not $unassignedElement) {
        throw "The current article collection could not be determined."
    }
    $collectionTrigger = [System.Windows.Automation.TreeWalker]::RawViewWalker.GetParent(
        $unassignedElement
    )
    $collectionTrigger.GetCurrentPattern(
        [System.Windows.Automation.InvokePattern]::Pattern
    ).Invoke()
    Start-Sleep -Milliseconds 600

    $collectionInputCondition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty,
        "请选择合集"
    )
    $collectionInput = $root.FindFirst(
        [System.Windows.Automation.TreeScope]::Descendants,
        $collectionInputCondition
    )
    if (-not $collectionInput) {
        throw "The collection selection dialog did not open."
    }
    $collectionInputRectangle = $collectionInput.Current.BoundingRectangle
    Invoke-PhysicalClick `
        -X ($collectionInputRectangle.Left + ($collectionInputRectangle.Width / 2)) `
        -Y ($collectionInputRectangle.Top + ($collectionInputRectangle.Height / 2))
    [System.Windows.Forms.Clipboard]::SetText($collectionName)
    [System.Windows.Forms.SendKeys]::SendWait("^a")
    [System.Windows.Forms.SendKeys]::SendWait("^v")
    Start-Sleep -Milliseconds 700

    $collectionMatches = $root.FindAll(
        [System.Windows.Automation.TreeScope]::Descendants,
        $collectionCondition
    )
    $collectionOption = $null
    foreach ($collectionMatch in $collectionMatches) {
        if ($collectionMatch.Current.ControlType -eq
            [System.Windows.Automation.ControlType]::ListItem) {
            $collectionOption = $collectionMatch
            break
        }
    }
    if (-not $collectionOption) {
        throw "The '$collectionName' collection option was not found."
    }
    $collectionOption.GetCurrentPattern(
        [System.Windows.Automation.InvokePattern]::Pattern
    ).Invoke()
    Start-Sleep -Milliseconds 300

    $confirmCollectionCondition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty,
        "确认"
    )
    $confirmCollectionButton = $root.FindFirst(
        [System.Windows.Automation.TreeScope]::Descendants,
        $confirmCollectionCondition
    )
    if (-not $confirmCollectionButton) {
        throw "The collection confirmation button was not found."
    }
    $confirmCollectionButton.GetCurrentPattern(
        [System.Windows.Automation.InvokePattern]::Pattern
    ).Invoke()
    Start-Sleep -Milliseconds 700

    $collectionArea = Get-ArticleCollectionArea -AutomationRoot $root
    $selectedCollection = $collectionArea.FindFirst(
        [System.Windows.Automation.TreeScope]::Descendants,
        $collectionCondition
    )
}
if (-not $selectedCollection) {
    throw "Collection validation failed: expected '$collectionName'."
}

$checks.PlatformRecommendation = $recommendation
$checks.PlatformRecommendationCount = $recommendationCount
$checks.OriginalLink = $doiUrl
$checks.Collection = $collectionName

$saved = $false
if ($SaveDraft) {
    $saveCondition = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::NameProperty,
        "保存为草稿"
    )
    $saveButton = $root.FindFirst(
        [System.Windows.Automation.TreeScope]::Descendants,
        $saveCondition
    )
    if (-not $saveButton) {
        throw "The Save as draft button was not found."
    }
    $saveButton.GetCurrentPattern(
        [System.Windows.Automation.InvokePattern]::Pattern
    ).Invoke()
    Start-Sleep -Seconds 6
    $saved = $true
}

[pscustomobject]@{
    headline = $headline
    doi = [string]$article.doi
    checks = $checks
    saved_as_draft = $saved
    published = $false
} | ConvertTo-Json -Depth 4 -Compress
