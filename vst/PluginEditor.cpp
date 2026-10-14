#include "PluginEditor.h"
#include "CoverArt.h"

namespace {
constexpr const char* kIDs[BassDriverAudioProcessor::kNumParams] = {
    "presence", "drive", "blend", "bass", "treble", "mid", "level", "mode"};
constexpr const char* kShort[BassDriverAudioProcessor::kNumParams] = {
    "PRESENCE", "DRIVE", "BLEND", "BASS", "TREBLE", "MID", "LEVEL", "MODE"};

void styleKnob(juce::Slider& s) {
    s.setSliderStyle(juce::Slider::RotaryHorizontalVerticalDrag);
    s.setTextBoxStyle(juce::Slider::TextBoxBelow, false, 58, 16);
    s.setColour(juce::Slider::rotarySliderFillColourId,
                juce::Colour(0xffe8a33d));
    s.setColour(juce::Slider::rotarySliderOutlineColourId,
                juce::Colour(0xff3a3a3a));
    s.setColour(juce::Slider::thumbColourId, juce::Colour(0xfff2e6d0));
    s.setColour(juce::Slider::textBoxTextColourId, juce::Colour(0xffd9d2c4));
    s.setColour(juce::Slider::textBoxOutlineColourId,
                juce::Colours::transparentBlack);
}

/* the on-device 1-bpp cover: per-cell 4x4 Bayer dither, same tone mapping
 * as tools/bddi_cover.py (K solid / k,D 75% / R 50% / P 25% / S,empty 0) */
juce::Image buildCoverImage(int px) {
    const int W = kCoverCols * px, H = kCoverRows * px;
    juce::Image img(juce::Image::ARGB, W, H, true);
    juce::Graphics g(img);
    g.fillAll(juce::Colours::white);
    static const int bayer[4][4] = {{0, 8, 2, 10}, {12, 4, 14, 6},
                                    {3, 11, 1, 9}, {15, 7, 13, 5}};
    auto tone = [](char c) {
        switch (c) {
            case 'K': return 16;
            case 'k': return 12;
            case 'D': return 12;
            case 'R': return 8;
            case 'P': return 4;
            default: return 0;
        }
    };
    g.setColour(juce::Colours::black);
    for (int j = 0; j < kCoverRows; ++j)
        for (int i = 0; i < kCoverCols; ++i)
            if (tone(kCoverGrid[j][i]) > bayer[j % 4][i % 4])
                g.fillRect(i * px, j * px, px, px);
    return img;
}
}  // namespace

BassDriverAudioProcessorEditor::BassDriverAudioProcessorEditor(
    BassDriverAudioProcessor& p)
    : AudioProcessorEditor(&p), proc(p) {
    coverImage = buildCoverImage(6);          /* 150 x 168 */

    for (int i = 0; i < BassDriverAudioProcessor::kNumParams; ++i) {
        auto& lab = nameLabels[i];
        lab.setText(kShort[i], juce::dontSendNotification);
        lab.setJustificationType(juce::Justification::centred);
        lab.setColour(juce::Label::textColourId, juce::Colour(0xffb9b2a6));
        lab.setFont(juce::FontOptions(12.0f, juce::Font::bold));
        addAndMakeVisible(lab);

        if (i == 7) break;                    /* mode is a combo box */
        auto& s = knobs[i];
        styleKnob(s);
        s.setName(kShort[i]);
        addAndMakeVisible(s);
        knobAtt[i] = std::make_unique<
            juce::AudioProcessorValueTreeState::SliderAttachment>(
            proc.apvts, kIDs[i], s);
    }
    modeBox.addItemList({"V1 late (2004+)", "V1 early (<=2003)", "V2 (2016+)"}, 1);
    modeBox.setColour(juce::ComboBox::backgroundColourId,
                      juce::Colour(0xff26262b));
    modeBox.setColour(juce::ComboBox::textColourId, juce::Colour(0xffd9d2c4));
    modeBox.setColour(juce::ComboBox::outlineColourId, juce::Colour(0xff3a3a3a));
    addAndMakeVisible(modeBox);
    modeAtt = std::make_unique<
        juce::AudioProcessorValueTreeState::ComboBoxAttachment>(
        proc.apvts, kIDs[7], modeBox);

    setSize(800, 360);
    setResizable(false, false);
}

void BassDriverAudioProcessorEditor::paint(juce::Graphics& g) {
    g.fillAll(juce::Colour(0xff17171a));

    auto head = getLocalBounds().reduced(16).removeFromTop(56);
    g.setColour(juce::Colour(0xffe8a33d));
    g.setFont(juce::FontOptions(27.0f, juce::Font::bold));
    g.drawText("BASS DRIVER", head.removeFromTop(32),
               juce::Justification::centredLeft);
    g.setColour(juce::Colour(0xff8f8a80));
    g.setFont(juce::FontOptions(12.5f));
    g.drawText("Tech 21 Bass Driver DI (V1 late) white-box replica -- "
               "same DSP core as the B1on ZDL",
               head.removeFromTop(16), juce::Justification::centredLeft);

    /* cover card */
    auto card = coverBounds.expanded(10);
    g.setColour(juce::Colour(0xfffffdf7));
    g.fillRoundedRectangle(card.toFloat(), 6.0f);
    g.setColour(juce::Colour(0xff2c2c30));
    g.drawRoundedRectangle(card.toFloat().reduced(0.5f), 6.0f, 1.0f);
    g.drawImageAt(coverImage, coverBounds.getX(), coverBounds.getY());

    g.setColour(juce::Colour(0xff8f8a80));
    g.setFont(juce::FontOptions(11.0f));
    g.drawText("BASSDRIVER.ZDL cover art", card.withY(card.getBottom() + 3)
                                           .withHeight(14),
               juce::Justification::centred);
}

void BassDriverAudioProcessorEditor::resized() {
    auto r = getLocalBounds().reduced(16);
    r.removeFromTop(62);
    auto left = r.removeFromLeft(190);
    coverBounds = juce::Rectangle<int>(0, 0, coverImage.getWidth(),
                                       coverImage.getHeight())
                      .withCentre(left.removeFromTop(190).getCentre());
    r.removeFromLeft(16);

    /* explicit 4x2 grid on the right of the cover card */
    auto grid = getLocalBounds().reduced(16);
    grid.removeFromTop(62);
    grid.removeFromLeft(206);
    const int cw = grid.getWidth() / 4, ch = grid.getHeight() / 2;
    for (int i = 0; i < 8; ++i) {
        const int col = i % 4, row = i / 4;
        auto cell = juce::Rectangle<int>(grid.getX() + col * cw,
                                         grid.getY() + row * ch, cw, ch)
                        .reduced(6, 8);
        nameLabels[i].setBounds(cell.removeFromTop(18));
        if (i < 7) {
            knobs[i].setBounds(cell.reduced(4, 2));
        } else {
            modeBox.setBounds(cell.reduced(6, 6).removeFromTop(30));
        }
    }
}
