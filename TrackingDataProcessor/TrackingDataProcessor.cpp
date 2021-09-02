// TrackingDataProcessor.cpp : This file contains the 'main' function. Program execution begins and ends there.
//

#include <ITK-5.1/itkImage.h>
#include <ITK-5.1/itkImageFileReader.h>
#include <ITK-5.1/itkImageFileWriter.h>
#include <ITK-5.1/itkMetaImageIOFactory.h>
#include <ITK-5.1/itkGDCMImageIOFactory.h>
#include <ITK-5.1/itkGDCMImageIO.h>
#include <ITK-5.1/itkMetaImageIO.h>
#include <ITK-5.1/itkTranslationTransform.h>
#include <ITK-5.1/itkResampleImageFilter.h>
#include <ITK-5.1/itkLinearInterpolateImageFunction.h>
#include <ITK-5.1/itkNearestNeighborInterpolateImageFunction.h>
#include <ITK-5.1/itkTileImageFilter.h>

#include <filesystem>
#include <string>
#include <vector>
#include <iostream>
#include <fstream>

/// <summary>
/// Retrieves the orientation as a 3DSlicer orientatin name based on the direction
/// of the image
/// </summary>
template <typename TImage>
std::string RetrieveOrientation(const itk::SmartPointer<TImage> img) {
    if (img->ImageDimension == 3) {

        std::string orientation = "Oblique";
        const itk::Image<float, 3>::DirectionType& direct = img->GetDirection();

        if (round(std::abs(direct[0][2])) == 1) {
            orientation = "Sagittal";
        }
        else if (round(std::abs(direct[1][2])) == 1) {
            orientation = "Coronal";
        }
        else if (round(std::abs(direct[2][2])) == 1) {
            orientation = "Axial";
        }
        return orientation;
    }

    return "img";
}


/// <summary>
/// Assumes that all slices have the same orientation. Pulls the direction from
/// the first slice then writes all slices to the outpath with a name corresponding to the slice.
/// The outpathbase is the base path including the start of the file name. For example the outPathBase
/// c/d/e/img will produce files like a/d/e/img_Saggital_0.mha
/// </summary>
template <typename TImage>
void WriteCommonOrientationSlices(std::vector<itk::SmartPointer<TImage>>* slices, std::string outPathBase)
{
    using Writer = itk::ImageFileWriter<TImage>;
    using ImageIO = itk::MetaImageIO;

    ImageIO::Pointer io = ImageIO::New();

    std::string orientation = RetrieveOrientation((*slices)[0]);

    int img_number = 0;
    for (itk::SmartPointer<TImage> img : *slices)
    {
        itk::SmartPointer<Writer> img_writer = Writer::New();
        img_writer->SetImageIO(io);
        img_writer->SetFileName(outPathBase + "_" + RetrieveOrientation(img) + "_" + std::to_string(img_number++) + ".mha");
        img_writer->SetInput(img);
        img_writer->Update();
    }
}

// --- Left here for notes ---
// This function shows you how to take a 2D series of images and write them into a 3D image

//template <typename TImage>
//void WriteToSlices(std::vector<itk::SmartPointer<TImage>>* slices, std::string outpath)
//{
//    using Writer = itk::ImageFileWriter<TImage>;
//    using ImageIO = itk::MetaImageIO;
//    using Tiler = itk::TileImageFilter<TImage, TImage>;
//
//    ImageIO::Pointer io = ImageIO::New();
//
//    itk::FixedArray<unsigned int, TImage::ImageDimension> layout;
//    layout[0] = 1;
//    layout[1] = 1;
//    layout[2] = 0;
//
//    // write images
//    itk::SmartPointer<Tiler> img_tiler = Tiler::New();
//    img_tiler->SetLayout(layout);
//
//    int img_number = 0;
//    for (itk::SmartPointer<TImage> img : *slices)
//    {
//        img_tiler->SetInput(img_number++, img);
//
//        itk::SmartPointer<Writer> img_writer = Writer::New();
//        img_writer->SetImageIO(io);
//        img_writer->SetFileName(outpath + RetrieveOrientation(img) + "_" + std::to_string(img_number++) + ".mha");
//        img_writer->SetInput(img);
//        img_writer->Update();
//    }
//
//    // TEMP REMOVE
//    //itk::SmartPointer<Writer> img_writer = Writer::New();
//    //img_writer->SetImageIO(io);
//    //img_writer->SetFileName(outpath);
//    //img_writer->SetInput(img_tiler->GetOutput());
//    //img_writer->Update();
//}

/// <summary>
/// Simplw equality between matricies
/// </summary>
bool MatrixEquals(itk::Matrix<double> mat1, itk::Matrix<double> mat2)
{
    for (int i = 0; i < 3; i++) {
        for (int j = 0; j < 3; j++) {
            if (mat1[i][j] != mat2[i][j]) return false;
        }
    }

    return true;
}

/// <summary>
/// Program converts a track package into data that can be interpreted by the Track
/// module in 3DSlicer (also present in this repo). It expects a series of images, 
/// lets say img1, img2, etc., A Segmentation.mha as a 3D volume, and a Transforms.csv with translation
/// data X, Y, Z, corresponding to the translation required to line up imgX with the segmentation. 
/// That being said, entry1 of the translation csv must correspond to the translation between img1 and
/// Segmentation.mha so that applying this translation to img1 causes the mask in Segmentation.mha
/// to cover the area of interest based on the results of a previous registration of the segmentation. 
/// The program will output another folder, with data ready to be visualized by 3D Slicer.
/// </summary>
int main(int argc, char* argv[])
{
    if (argc == 1) {
        std::cout << "You must supply a path to a valid folder";
    }

    using ImageIO = itk::MetaImageIO;
    using Image = itk::Image<float, 3>;
    using Tiler = itk::TileImageFilter<Image, Image>;
    using Reader = itk::ImageFileReader<Image>;
    using Writer = itk::ImageFileWriter<Image>;
    using Transform = itk::TranslationTransform<>;
    using Resampler = itk::ResampleImageFilter<Image, Image>;
    using Interpolator = itk::NearestNeighborInterpolateImageFunction<Image>;

    // extract the paths expected in the package
    std::string input_path = argv[1];
    std::string output_path = input_path + "_output";

    if (!std::filesystem::exists(output_path))
    {
        std::filesystem::create_directory(output_path);
    }

    std::filesystem::path translations_path;
    std::filesystem::path segmentation_path;
    std::vector<std::filesystem::path> image_paths;

    for (const std::filesystem::directory_entry& entry : std::filesystem::directory_iterator(input_path))
    {
        std::string path = entry.path().string();

        if (path.find("Segmentation") != -1) segmentation_path = path;
        else if (path.find("Transforms") != -1) translations_path = path;
        else if (path.find("Volume3D") != -1) continue;
        else image_paths.push_back(path);
    }

    // extract translations from csv
    std::ifstream translation_data_file(translations_path);
    std::vector<std::string> translation_data;

    bool is_first_line = true;
    if (translation_data_file.is_open()) {

        while (translation_data_file.good()) {

            std::string line;
            std::getline(translation_data_file, line);

            if (is_first_line) {
                is_first_line = false;
                continue;
            }

            translation_data.push_back(line);
        }
    }

    // convert to float data
    std::vector<Transform::Pointer> translations;
    for (std::string s : translation_data)
    {
        std::vector<std::string> split_data;

        int last_start = 0;
        for (int i = 0; i < 3; i++) {
            int comma_index = s.find(',', last_start);
            split_data.push_back(s.substr(last_start, comma_index - last_start));
            last_start = comma_index + 1;
        }

        Transform::OutputVectorType vector;
        try
        {
            vector[0] = std::stof(split_data[0]);
            vector[1] = std::stof(split_data[1]);
            vector[2] = std::stof(split_data[2]);
        }
        catch (...)
        {
            continue;
        }

        Transform::Pointer translation = Transform::New();
        translation->Translate(vector);
        translations.push_back(translation);
    }

    // Setup shared resources
    ImageIO::Pointer io = ImageIO::New();
    Interpolator::Pointer inteprolator = Interpolator::New();

    // prepare the segmentation volume
    Reader::Pointer seg_reader = Reader::New();
    seg_reader->SetImageIO(io);
    seg_reader->SetFileName(segmentation_path.string());
    seg_reader->Update();

    Image::Pointer segmentation_image = seg_reader->GetOutput();

    // read the image
    if (translations.size() != image_paths.size()) {
        std::cout << "[WARNING] There is a count miss match between translations and images. There are "
            << translations.size() << "translations and "
            << image_paths.size() << "image_paths"
            << std::endl;
    }

    itk::Matrix<double> orientation[3];
    std::vector<Image::Pointer> out_ref[3];
    std::vector<Image::Pointer> out_seg[3];

    // Process each translation
    int registered_orientations = 0;
    for (int i = 0; i < translations.size(); i++)
    {
        // read the target image
        Reader::Pointer ref_reader = Reader::New();

        ref_reader->SetImageIO(io);
        ref_reader->SetFileName(image_paths[i].string());
        ref_reader->Update();
        Image::Pointer reference_image = ref_reader->GetOutput();

        // find the index of the direction matrix. This will be used to
        // story the data in the correct vector
        itk::Matrix<double> matrix = reference_image->GetDirection();

        int orientation_index = -1;
        for (int j = 0; j < registered_orientations; j++)
        {
            if (MatrixEquals(matrix, orientation[j]))
            {
                orientation_index = j;
                break;
            }
        }

        // This line registers the orientaiton, if the orientation is not already
        // present in the orientations matrix
        if (orientation_index == -1) {
            orientation[registered_orientations] = matrix;
            orientation_index = registered_orientations++;
        }

        // Add the image to the orientation vector
        out_ref[orientation_index].push_back(reference_image);

        // Perform a resampling on the Segmentation.mha so that
        // it overlays over the point of interest
        Transform::Pointer trans = translations[i];

        Resampler::Pointer resampler = Resampler::New();
        resampler->SetInput(segmentation_image);
        resampler->SetOutputParametersFromImage(reference_image);
        resampler->SetTransform(trans->GetInverseTransform());
        resampler->SetInterpolator(inteprolator);
        resampler->Update();

        // Add the segmentaiton to the segmentaion vector
        out_seg[orientation_index].push_back(resampler->GetOutput());
    }

    // output all unpacked data into img and seg files.
    // These files will also include orientation and order information
    // in their name. THey will save in the same place as the original
    // folder with _ouput appended to the name
    for (int i = 0; i < registered_orientations; i++)
    {
        WriteCommonOrientationSlices<Image>(&out_ref[i], output_path + "/img");
        WriteCommonOrientationSlices<Image>(&out_seg[i], output_path + "/seg");
    }

    return 1;
}